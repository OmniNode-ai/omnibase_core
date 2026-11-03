# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-13857: ``onex run-node`` fails fast with an actionable message.

Before this fix an unreachable broker surfaced an opaque
``confluent_kafka.KafkaException`` (``_TRANSPORT``). It now emits a single
actionable error that points the operator at the bus-less ``onex run <node>``
fallback. The broker itself is no longer an environment variable (OMN-22362).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from tests.unit.cli.node_broker_fixtures import RESOLVER_PATCH_TARGET, kafka_binding

pytestmark = pytest.mark.unit

_PATCH_PRODUCER = "confluent_kafka.Producer"
_PATCH_CONSUMER = "confluent_kafka.Consumer"
_PATCH_TOPIC_PARTITION = "confluent_kafka.TopicPartition"


class _FakeTopicPartition:
    def __init__(self, topic: str, partition: int, offset: int | None = None) -> None:
        self.topic = topic
        self.partition = partition
        self.offset = offset


class TestBrokerComesFromTheOverlayOnly:
    """OMN-22362 supersedes the env-var form of OMN-13857: no variable names the broker."""

    def test_binding_broker_is_dialed_and_env_is_ignored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from omnibase_core.cli.cli_run_node import run_node

        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "ambient-env:1")
        with (
            patch(RESOLVER_PATCH_TARGET, return_value=kafka_binding("lane-host:39092")),
            patch(
                "omnibase_core.cli.cli_run_node._resolve_node_topics",
                return_value=("/tmp/c.yaml", "cmd.v1", "evt.v1", False),
            ),
            patch(
                "omnibase_core.cli.cli_run_node.publish_and_poll",
                return_value={"payload": {"ok": True}},
            ) as dial,
        ):
            result = CliRunner().invoke(run_node, ["node_x", "--input", "{}"])
        assert result.exit_code == 0
        assert dial.call_args.kwargs["bootstrap_servers"] == "lane-host:39092"

    def test_no_resolver_installed_exits_with_actionable_error(self) -> None:
        from omnibase_core.cli.cli_run_node import run_node

        with patch(
            "omnibase_core.models.event_bus.model_node_broker_binding.entry_points",
            return_value=[],
        ):
            result = CliRunner().invoke(run_node, ["node_dod_verify", "--input", "{}"])
        assert result.exit_code == 1
        assert "onex.node_broker_resolvers" in result.output
        assert "KAFKA_BOOTSTRAP_SERVERS" not in result.output


class TestUnreachableBrokerWrapped:
    def test_transport_failure_wrapped_as_actionable_error(self) -> None:
        from omnibase_core.cli.cli_run_node import publish_and_poll
        from omnibase_core.errors import OnexError

        # Simulate the raw confluent_kafka.KafkaException (_TRANSPORT) the first
        # broker touch raises when the bootstrap address is unreachable.
        consumer = MagicMock()
        consumer.list_topics.side_effect = RuntimeError(
            "KafkaError{code=_TRANSPORT,val=-195,str=Broker transport failure}"
        )

        with (
            patch(_PATCH_TOPIC_PARTITION, side_effect=_FakeTopicPartition),
            patch(_PATCH_PRODUCER, return_value=MagicMock()),
            patch(_PATCH_CONSUMER, return_value=consumer),
        ):
            with pytest.raises(OnexError, match="unreachable") as exc_info:
                publish_and_poll(
                    node_id="node_dod_verify",
                    payload={},
                    timeout=5,
                    bootstrap_servers="unreachable-host:19092",
                    command_topic="onex.cmd.test.command.v1",
                    response_topic="onex.evt.test.completed.v1",
                )
        message = str(exc_info.value)
        assert "unreachable-host:19092" in message
        assert "onex run node_dod_verify" in message
        # The consumer must still be closed on the failure path.
        consumer.close.assert_called_once()
