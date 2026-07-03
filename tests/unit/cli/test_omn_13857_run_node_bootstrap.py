# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-13857: ``onex run-node`` fails fast with an actionable message.

Before this fix, an unset ``KAFKA_BOOTSTRAP_SERVERS`` raised a bare ``KeyError``
traceback and an unreachable broker surfaced an opaque
``confluent_kafka.KafkaException`` (``_TRANSPORT``). Both now emit a single
actionable error that points the operator at the reachable-lane env var or the
bus-less ``onex run <node>`` fallback.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

pytestmark = pytest.mark.unit

_PATCH_PRODUCER = "confluent_kafka.Producer"
_PATCH_CONSUMER = "confluent_kafka.Consumer"
_PATCH_TOPIC_PARTITION = "confluent_kafka.TopicPartition"


class _FakeTopicPartition:
    def __init__(self, topic: str, partition: int, offset: int | None = None) -> None:
        self.topic = topic
        self.partition = partition
        self.offset = offset


class TestResolveBootstrapServers:
    def test_returns_value_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from omnibase_core.cli.cli_run_node import _resolve_bootstrap_servers

        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "lane-host:39092")
        assert _resolve_bootstrap_servers("node_x") == "lane-host:39092"

    def test_unset_exits_with_actionable_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from omnibase_core.cli.cli_run_node import run_node

        monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)
        result = CliRunner().invoke(run_node, ["node_dod_verify", "--input", "{}"])
        assert result.exit_code == 1
        assert "KAFKA_BOOTSTRAP_SERVERS is not set" in result.output
        assert "onex run node_dod_verify" in result.output

    def test_empty_exits_with_actionable_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from omnibase_core.cli.cli_run_node import run_node

        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "   ")
        result = CliRunner().invoke(run_node, ["node_dod_verify", "--input", "{}"])
        assert result.exit_code == 1
        assert "KAFKA_BOOTSTRAP_SERVERS is not set" in result.output


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
