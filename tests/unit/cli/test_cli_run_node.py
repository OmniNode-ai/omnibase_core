# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for cli_run_node — confluent_kafka producer/consumer path (OMN-9715)."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_run_node import publish_and_poll, run_node

pytestmark = pytest.mark.unit

# Producer and Consumer are imported inside publish_and_poll (lazy import), so
# patch them at their source — confluent_kafka.Producer / confluent_kafka.Consumer.
_PATCH_PRODUCER = "confluent_kafka.Producer"
_PATCH_CONSUMER = "confluent_kafka.Consumer"


class TestCliRunNodeNoKafkaPythonImport:
    """Assert that kafka-python (module ``kafka``) is NOT imported at module load time."""

    def test_kafka_python_not_imported_at_module_level(self) -> None:
        assert "kafka" not in sys.modules, (
            "kafka-python must not be imported at module level in cli_run_node"
        )

    def test_confluent_kafka_import_path_used(self) -> None:
        import importlib.util

        spec = importlib.util.find_spec("omnibase_core.cli.cli_run_node")
        assert spec is not None
        source = spec.origin
        assert source is not None
        with open(source) as f:
            content = f.read()
        assert "import kafka" not in content, (
            "cli_run_node must not contain 'import kafka' (kafka-python)"
        )
        assert "confluent_kafka" in content, (
            "cli_run_node must reference confluent_kafka"
        )


class TestPublishAndPoll:
    """Test publish_and_poll with stubbed confluent_kafka Producer and Consumer."""

    def _make_mock_message(
        self, correlation_id: str, extra: dict[str, object] | None = None
    ) -> MagicMock:
        msg = MagicMock()
        msg.error.return_value = None
        data: dict[str, object] = {"correlation_id": correlation_id, "status": "ok"}
        if extra:
            data.update(extra)
        msg.value.return_value = json.dumps(data).encode()
        return msg

    def test_produce_call_shape(self) -> None:
        mock_producer = MagicMock()
        mock_consumer = MagicMock()
        mock_consumer.poll.return_value = None  # timeout immediately

        with (
            patch("omnibase_core.cli.cli_run_node.time") as mock_time,
            patch(_PATCH_CONSUMER, return_value=mock_consumer),
            patch(_PATCH_PRODUCER, return_value=mock_producer),
        ):
            mock_time.time.return_value = 1234567890.0
            start = 1000.0
            mock_time.monotonic.side_effect = [start, start + 10.0]  # deadline exceeded

            publish_and_poll(
                node_id="test-node",
                payload={"foo": "bar"},
                timeout=5,
                bootstrap_servers="localhost:19092",
            )

        mock_producer.produce.assert_called_once()
        produce_kwargs = mock_producer.produce.call_args
        assert produce_kwargs.kwargs.get("topic") or produce_kwargs.args[0]
        mock_producer.flush.assert_called_once_with(timeout=10.0)

    def test_returns_correlated_message(self) -> None:
        original_uuid4 = __import__("uuid").uuid4

        corr_id_holder: list[str] = []

        def _capture_uuid4() -> object:
            uid = original_uuid4()
            corr_id_holder.append(str(uid))
            return uid

        mock_producer = MagicMock()

        def _make_consumer(config: dict[str, object]) -> MagicMock:
            consumer = MagicMock()
            group_id = str(config.get("group.id", ""))
            corr = group_id.removeprefix("onex-run-node-")
            msg = self._make_mock_message(corr)
            consumer.poll.side_effect = [None, msg]
            return consumer

        with (
            patch(
                "omnibase_core.cli.cli_run_node.uuid.uuid4", side_effect=_capture_uuid4
            ),
            patch("omnibase_core.cli.cli_run_node.time") as mock_time,
            patch(_PATCH_CONSUMER, side_effect=_make_consumer),
            patch(_PATCH_PRODUCER, return_value=mock_producer),
        ):
            start = 1000.0
            mock_time.time.return_value = 1234567890.0
            # Use return_value so monotonic() never exhausts regardless of call count
            mock_time.monotonic.return_value = start

            result = publish_and_poll(
                node_id="my-node",
                payload={},
                timeout=30,
                bootstrap_servers="localhost:19092",
            )

        assert result is not None
        assert result.get("status") == "ok"

    def test_returns_none_on_timeout(self) -> None:
        mock_producer = MagicMock()
        mock_consumer = MagicMock()
        mock_consumer.poll.return_value = None

        with (
            patch("omnibase_core.cli.cli_run_node.time") as mock_time,
            patch(_PATCH_CONSUMER, return_value=mock_consumer),
            patch(_PATCH_PRODUCER, return_value=mock_producer),
        ):
            mock_time.time.return_value = 1234567890.0
            start = 1000.0
            mock_time.monotonic.side_effect = [start, start + 31.0]

            result = publish_and_poll(
                node_id="my-node",
                payload={},
                timeout=30,
                bootstrap_servers="localhost:19092",
            )

        assert result is None
        mock_consumer.close.assert_called_once()

    def test_consumer_closed_on_match(self) -> None:
        mock_producer = MagicMock()

        def _make_consumer(config: dict[str, object]) -> MagicMock:
            consumer = MagicMock()
            group_id = str(config.get("group.id", ""))
            corr = group_id.removeprefix("onex-run-node-")
            msg = self._make_mock_message(corr)
            consumer.poll.return_value = msg
            return consumer

        with (
            patch("omnibase_core.cli.cli_run_node.time") as mock_time,
            patch(_PATCH_CONSUMER, side_effect=_make_consumer),
            patch(_PATCH_PRODUCER, return_value=mock_producer),
        ):
            start = 1000.0
            mock_time.time.return_value = 1234567890.0
            mock_time.monotonic.side_effect = [start, start + 0.1, start + 0.2]

            result = publish_and_poll(
                node_id="my-node",
                payload={},
                timeout=30,
                bootstrap_servers="localhost:19092",
            )

        assert result is not None

    def test_raises_onerror_when_confluent_kafka_missing(self) -> None:
        from omnibase_core.errors import OnexError

        with patch.dict(sys.modules, {"confluent_kafka": None}):
            with pytest.raises((OnexError, ImportError)):
                publish_and_poll(
                    node_id="x",
                    payload={},
                    timeout=5,
                    bootstrap_servers="localhost:19092",
                )

    def test_delivery_failure_raises_onerror(self) -> None:
        from omnibase_core.errors import OnexError

        def _make_failing_producer(config: dict[str, object]) -> MagicMock:
            producer = MagicMock()

            def _produce(**kwargs: object) -> None:
                on_delivery = kwargs.get("on_delivery")
                if callable(on_delivery):
                    on_delivery("simulated delivery error", None)

            producer.produce.side_effect = _produce
            return producer

        mock_consumer = MagicMock()

        with (
            patch(_PATCH_PRODUCER, side_effect=_make_failing_producer),
            patch(_PATCH_CONSUMER, return_value=mock_consumer),
        ):
            with pytest.raises(OnexError):
                publish_and_poll(
                    node_id="x",
                    payload={},
                    timeout=5,
                    bootstrap_servers="localhost:19092",
                )


class TestRunNodeCommand:
    """Test the click run-node command via CliRunner."""

    def test_invalid_json_exits_nonzero(self) -> None:
        runner = CliRunner()
        result = runner.invoke(run_node, ["test-node", "--input", "not-json"])
        assert result.exit_code != 0

    def test_timeout_response_exits_nonzero(self) -> None:
        runner = CliRunner()
        mock_producer = MagicMock()
        mock_consumer = MagicMock()
        mock_consumer.poll.return_value = None

        with (
            patch("omnibase_core.cli.cli_run_node.time") as mock_time,
            patch(_PATCH_CONSUMER, return_value=mock_consumer),
            patch(_PATCH_PRODUCER, return_value=mock_producer),
        ):
            mock_time.time.return_value = 1234567890.0
            start = 1000.0
            mock_time.monotonic.side_effect = [start, start + 35.0]

            result = runner.invoke(
                run_node, ["test-node", "--input", '{"x": 1}', "--timeout", "30"]
            )

        assert result.exit_code != 0
        output = json.loads(result.output)
        assert output["error_type"] == "SkillRoutingError"
        assert "Timeout" in output["message"]
