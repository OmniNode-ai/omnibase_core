# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Envelope compatibility proof: CLI outbound shape vs runtime deserialization (OMN-10517).

As of OMN-9877 the CLI uses ModelEventEnvelope as the outbound wire format:
    {"payload": dict, "correlation_id": UUID-str, "source_tool": str,
     "target_tool": str, ...metadata...}

ModelDispatchBusCommand (runtime pattern-B broker) expects:
    {"command_name": str, "requester": str, "payload": ..., "correlation_id": UUID,
     "response_topic": str, ...}
These shapes remain incompatible — the CLI topic (onex.cmd.platform.run-node.v1)
has no registered runtime consumer that reads ModelDispatchBusCommand.

This test file asserts the CLI-produced ModelEventEnvelope CAN be round-tripped
through the runtime's deserialization path and is internally self-consistent.
"""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


_PATCH_TOPIC_PARTITION = "confluent_kafka.TopicPartition"


class _FakeTopicPartition:
    def __init__(self, topic: str, partition: int, offset: int | None = None) -> None:
        self.topic = topic
        self.partition = partition
        self.offset = offset


def _make_assigned_consumer(
    response_topic: str = "onex.evt.test.completed.v1",
) -> MagicMock:
    consumer = MagicMock()
    topic_metadata = MagicMock()
    topic_metadata.partitions = {0: object()}
    topic_metadata.error = None
    metadata = MagicMock()
    metadata.topics = {response_topic: topic_metadata}
    consumer.list_topics.return_value = metadata
    consumer.poll.return_value = None
    return consumer


class TestCliEnvelopeShape:
    """Assert the CLI outbound envelope uses ModelEventEnvelope (OMN-9877)."""

    def test_cli_envelope_fields_present(self) -> None:
        """CLI envelope must be a ModelEventEnvelope with correlation_id, payload, target_tool."""
        from unittest.mock import patch

        from omnibase_core.cli.cli_run_node import publish_and_poll

        captured: list[dict[str, Any]] = []

        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0

        def _capture_produce(**kwargs: Any) -> None:
            raw = kwargs.get("value", b"")
            captured.append(json.loads(raw.decode()))

        mock_producer.produce.side_effect = _capture_produce

        mock_consumer = _make_assigned_consumer()

        with (
            patch(
                "omnibase_core.cli.cli_run_node.time.monotonic",
                side_effect=iter([1000.0, 1000.0, 1050.0]),
            ),
            patch(_PATCH_TOPIC_PARTITION, side_effect=_FakeTopicPartition),
            patch("confluent_kafka.Consumer", return_value=mock_consumer),
            patch("confluent_kafka.Producer", return_value=mock_producer),
        ):
            publish_and_poll(
                node_id="test-node-abc",
                payload={"key": "value"},
                timeout=5,
                bootstrap_servers="localhost:19092",
                command_topic="onex.cmd.test.node-start.v1",
                response_topic="onex.evt.test.completed.v1",
            )

        assert len(captured) == 1
        envelope = captured[0]
        assert "correlation_id" in envelope
        assert "payload" in envelope
        assert "target_tool" in envelope
        assert envelope["target_tool"] == "test-node-abc"
        assert envelope["payload"] == {"key": "value"}
        assert envelope["source_tool"] == "onex.run-node"

    def test_cli_correlation_id_is_string_uuid(self) -> None:
        """CLI correlation_id must be a string-formatted UUID."""
        from unittest.mock import patch

        from omnibase_core.cli.cli_run_node import publish_and_poll

        captured: list[dict[str, Any]] = []

        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0

        def _capture(
            topic: str | None = None, value: bytes | None = None, **kwargs: Any
        ) -> None:
            if value:
                captured.append(json.loads(value.decode()))

        mock_producer.produce.side_effect = _capture
        mock_consumer = _make_assigned_consumer()

        with (
            patch(
                "omnibase_core.cli.cli_run_node.time.monotonic",
                side_effect=iter([1000.0, 1000.0, 1050.0]),
            ),
            patch(_PATCH_TOPIC_PARTITION, side_effect=_FakeTopicPartition),
            patch("confluent_kafka.Consumer", return_value=mock_consumer),
            patch("confluent_kafka.Producer", return_value=mock_producer),
        ):
            publish_and_poll(
                node_id="n1",
                payload={},
                timeout=5,
                bootstrap_servers="localhost:19092",
                command_topic="onex.cmd.test.node-start.v1",
                response_topic="onex.evt.test.completed.v1",
            )

        assert len(captured) == 1
        corr_id = captured[0]["correlation_id"]
        # Must be parseable as UUID
        parsed = uuid.UUID(corr_id)
        assert str(parsed) == corr_id


class TestCliEnvelopeVsModelDispatchBusCommand:
    """Assert the CLI envelope shape is documented as divergent from ModelDispatchBusCommand."""

    def test_cli_envelope_not_compatible_with_dispatch_bus_command(self) -> None:
        """ModelEventEnvelope CANNOT be deserialized into ModelDispatchBusCommand.

        Documents the known divergence: the CLI topic is informal and not
        consumed by the pattern-B broker runtime path.
        """
        from pydantic import ValidationError

        from omnibase_core.models.dispatch.model_dispatch_bus_command import (
            ModelDispatchBusCommand,
        )

        cli_envelope = {
            "correlation_id": str(uuid.uuid4()),
            "payload": {"x": 1},
            "source_tool": "onex.run-node",
            "target_tool": "test-node",
        }

        # CLI envelope lacks required fields and has forbidden extras
        with pytest.raises(ValidationError):
            ModelDispatchBusCommand(**cli_envelope)

    def test_dispatch_bus_command_fields_not_in_cli_envelope(self) -> None:
        """ModelDispatchBusCommand requires fields absent from CLI ModelEventEnvelope."""
        from omnibase_core.models.dispatch.model_dispatch_bus_command import (
            ModelDispatchBusCommand,
        )

        required_fields = {
            name
            for name, field in ModelDispatchBusCommand.model_fields.items()
            if field.is_required()
        }
        cli_envelope_fields = {
            "correlation_id",
            "payload",
            "source_tool",
            "target_tool",
        }

        missing_from_cli = required_fields - cli_envelope_fields
        assert missing_from_cli, (
            "ModelDispatchBusCommand has required fields that the CLI envelope "
            f"does not provide: {missing_from_cli}"
        )


class TestHandlerBusAdapterWithCliEnvelope:
    """Assert HandlerBusAdapter deserializes the CLI envelope shape correctly.

    Since the CLI topic has no registered HandlerBusAdapter consumer in production,
    this test proves that a custom input model matching the CLI shape CAN be wired
    via the HandlerBusAdapter deserialization path without error.
    """

    def test_handler_bus_adapter_deserializes_cli_shape(self) -> None:
        """HandlerBusAdapter can deserialize a ModelEventEnvelope-shaped message into a matching model."""
        from pydantic import BaseModel, ConfigDict

        from omnibase_core.runtime.runtime_local_adapter import HandlerBusAdapter

        class ModelCliRunNodeCommand(BaseModel):
            model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)
            correlation_id: str
            payload: dict[str, Any]
            target_tool: str
            source_tool: str

        received: list[ModelCliRunNodeCommand] = []

        class _FakeHandler:
            def handle(self, **kwargs: Any) -> None:
                received.append(ModelCliRunNodeCommand(**kwargs))

        bus = MagicMock()
        bus.publish = AsyncMock()

        adapter = HandlerBusAdapter(
            handler=_FakeHandler(),
            handler_name="FakeHandler",
            input_model_cls=ModelCliRunNodeCommand,
            output_topic=None,
            bus=bus,
        )

        corr_id = str(uuid.uuid4())
        cli_envelope = {
            "correlation_id": corr_id,
            "payload": {"param": "value"},
            "target_tool": "synthetic-node",
            "source_tool": "onex.run-node",
        }
        msg = MagicMock()
        msg.value = json.dumps(cli_envelope).encode("utf-8")

        import asyncio

        asyncio.run(adapter.on_message(msg))

        assert len(received) == 1
        assert received[0].correlation_id == corr_id
        assert received[0].target_tool == "synthetic-node"
        assert received[0].payload == {"param": "value"}

    def test_handler_bus_adapter_fails_on_mismatched_model(self) -> None:
        """HandlerBusAdapter error callback fires when CLI envelope hits incompatible model."""
        from omnibase_core.models.dispatch.model_dispatch_bus_command import (
            ModelDispatchBusCommand,
        )
        from omnibase_core.runtime.runtime_local_adapter import HandlerBusAdapter

        error_fired: list[bool] = []

        class _FakeHandler:
            def handle(self, **kwargs: Any) -> None:
                pass  # pragma: no cover

        bus = MagicMock()
        bus.publish = AsyncMock()

        adapter = HandlerBusAdapter(
            handler=_FakeHandler(),
            handler_name="FakeHandler",
            input_model_cls=ModelDispatchBusCommand,
            output_topic=None,
            bus=bus,
            on_error=lambda: error_fired.append(True),
        )

        cli_envelope = {
            "correlation_id": str(uuid.uuid4()),
            "payload": {"x": 1},
            "target_tool": "test-node",
            "source_tool": "onex.run-node",
        }
        msg = MagicMock()
        msg.value = json.dumps(cli_envelope).encode("utf-8")

        import asyncio

        asyncio.run(adapter.on_message(msg))

        assert error_fired, (
            "Expected on_error to fire when CLI envelope is fed to "
            "ModelDispatchBusCommand adapter"
        )


class TestCliEnvelopeRoundTrip:
    """Assert CLI envelope serializes and deserializes without data loss."""

    def test_cli_envelope_json_roundtrip(self) -> None:
        """ModelEventEnvelope-shaped CLI envelope survives JSON encode/decode without data loss."""
        corr_id = str(uuid.uuid4())
        original = {
            "correlation_id": corr_id,
            "payload": {"nested": {"a": 1}, "list": [1, 2, 3]},
            "source_tool": "onex.run-node",
            "target_tool": "node-xyz",
        }

        raw = json.dumps(original).encode("utf-8")
        decoded: dict[str, Any] = json.loads(raw.decode("utf-8"))

        assert decoded == original
        assert decoded["correlation_id"] == corr_id
        assert decoded["target_tool"] == "node-xyz"
        assert decoded["payload"] == {"nested": {"a": 1}, "list": [1, 2, 3]}

    def test_correlated_response_matches_sent_correlation_id(self) -> None:
        """publish_and_poll returns only the response with the matching correlation_id."""
        from unittest.mock import patch

        from omnibase_core.cli.cli_run_node import publish_and_poll

        original_uuid4 = uuid.uuid4
        corr_id_holder: list[str] = []

        def _capture_uuid4() -> uuid.UUID:
            uid = original_uuid4()
            corr_id_holder.append(str(uid))
            return uid

        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0

        def _make_consumer(config: dict[str, Any]) -> MagicMock:
            consumer = MagicMock()
            group_id = str(config.get("group.id", ""))
            corr = group_id.removeprefix("onex-run-node-")

            topic_metadata = MagicMock()
            topic_metadata.partitions = {0: object()}
            topic_metadata.error = None
            metadata = MagicMock()
            metadata.topics = {"onex.evt.test.completed.v1": topic_metadata}
            consumer.list_topics.return_value = metadata

            wrong_msg = MagicMock()
            wrong_msg.error.return_value = None
            wrong_msg.value.return_value = json.dumps(
                {"correlation_id": str(uuid.uuid4()), "status": "wrong"}
            ).encode()

            right_msg = MagicMock()
            right_msg.error.return_value = None
            right_msg.value.return_value = json.dumps(
                {"correlation_id": corr, "status": "correct"}
            ).encode()

            consumer.poll.side_effect = [wrong_msg, right_msg]
            return consumer

        with (
            patch(
                "omnibase_core.cli.cli_run_node.uuid.uuid4", side_effect=_capture_uuid4
            ),
            patch("omnibase_core.cli.cli_run_node.time") as mock_time,
            patch(_PATCH_TOPIC_PARTITION, side_effect=_FakeTopicPartition),
            patch("confluent_kafka.Consumer", side_effect=_make_consumer),
            patch("confluent_kafka.Producer", return_value=mock_producer),
        ):
            mock_time.monotonic.return_value = 1000.0

            result = publish_and_poll(
                node_id="my-node",
                payload={"input": 42},
                timeout=30,
                bootstrap_servers="localhost:19092",
                command_topic="onex.cmd.test.command.v1",
                response_topic="onex.evt.test.completed.v1",
            )

        assert result is not None
        assert result["status"] == "correct"
        assert len(corr_id_holder) >= 1
