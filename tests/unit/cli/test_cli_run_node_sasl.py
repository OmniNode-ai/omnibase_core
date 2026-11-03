# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-17427, reshaped by OMN-22362: ``onex run-node`` authenticates to a SASL lane broker.

The .201 dev lane's broker requires SASL_PLAINTEXT with SCRAM-SHA-256. The client
security configuration used to come from ``KAFKA_SECURITY_PROTOCOL`` /
``KAFKA_SASL_*``; since OMN-22362 it comes from the resolved binding that the
node's contract overlay names, and no environment variable reaches the dispatch.
These tests pin the binding to the clients and keep the credential out of every
error message.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from tests.unit.cli.node_broker_fixtures import (
    RESOLVER_PATCH_TARGET,
    kafka_binding,
)

pytestmark = pytest.mark.unit

_PATCH_PRODUCER = "confluent_kafka.Producer"
_PATCH_CONSUMER = "confluent_kafka.Consumer"
_PATCH_TOPIC_PARTITION = "confluent_kafka.TopicPartition"
_CREDENTIAL_MARKER = "credential-marker-never-printed"


class _FakeTopicPartition:
    def __init__(self, topic: str, partition: int, offset: int | None = None) -> None:
        self.topic = topic
        self.partition = partition
        self.offset = offset


class TestBindingClientSecurity:
    """The resolved binding, not the environment, carries the lane's client security."""

    def test_plaintext_lane_carries_only_its_declared_protocol(self) -> None:
        assert kafka_binding().client_security() == {"security.protocol": "PLAINTEXT"}

    def test_scram_lane_carries_the_full_config(self) -> None:
        assert kafka_binding(sasl_password=_CREDENTIAL_MARKER).client_security() == {
            "security.protocol": "SASL_PLAINTEXT",
            "sasl.mechanism": "SCRAM-SHA-256",
            "sasl.username": "dev-principal",
            "sasl.password": _CREDENTIAL_MARKER,
        }

    def test_binding_never_prints_the_password(self) -> None:
        binding = kafka_binding(sasl_password=_CREDENTIAL_MARKER)
        assert _CREDENTIAL_MARKER not in repr(binding)
        assert _CREDENTIAL_MARKER not in binding.model_dump_json()

    def test_ambient_sasl_env_does_not_reach_the_dispatch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from omnibase_core.cli.cli_run_node import run_node

        monkeypatch.setenv("KAFKA_SECURITY_PROTOCOL", "SASL_PLAINTEXT")
        monkeypatch.setenv("KAFKA_SASL_PASSWORD", _CREDENTIAL_MARKER)
        with (
            patch(RESOLVER_PATCH_TARGET, return_value=kafka_binding()),
            patch(
                "omnibase_core.cli.cli_run_node._resolve_node_topics",
                return_value=("/tmp/c.yaml", "cmd.v1", "evt.v1", False),
            ),
            patch(
                "omnibase_core.cli.cli_run_node.publish_and_poll",
                return_value={"payload": {}},
            ) as dial,
        ):
            result = CliRunner().invoke(run_node, ["node_x", "--input", "{}"])
        assert result.exit_code == 0
        assert dial.call_args.kwargs["client_security"] == {
            "security.protocol": "PLAINTEXT"
        }


class TestRunNodeAuthenticates:
    def test_consumer_and_producer_carry_the_sasl_config(self) -> None:
        from omnibase_core.cli.cli_run_node import publish_and_poll

        consumer = MagicMock()
        partition_meta = MagicMock()
        partition_meta.error = None
        partition_meta.partitions = {0: object()}
        consumer.list_topics.return_value.topics = {
            "onex.evt.test.completed.v1": partition_meta
        }
        consumer.poll.return_value = None
        producer = MagicMock()
        producer.flush.return_value = 0

        with (
            patch(_PATCH_TOPIC_PARTITION, side_effect=_FakeTopicPartition),
            patch(_PATCH_PRODUCER, return_value=producer) as producer_cls,
            patch(_PATCH_CONSUMER, return_value=consumer) as consumer_cls,
        ):
            assert (
                publish_and_poll(
                    node_id="node_dod_verify",
                    payload={},
                    timeout=0,
                    bootstrap_servers="redpanda:9092",
                    command_topic="onex.cmd.test.command.v1",
                    response_topic="onex.evt.test.completed.v1",
                    client_security=kafka_binding(
                        sasl_password=_CREDENTIAL_MARKER
                    ).client_security(),
                )
                is None
            )

        for client_cls in (consumer_cls, producer_cls):
            conf = client_cls.call_args.args[0]
            assert conf["bootstrap.servers"] == "redpanda:9092"
            assert conf["security.protocol"] == "SASL_PLAINTEXT"
            assert conf["sasl.mechanism"] == "SCRAM-SHA-256"
            assert conf["sasl.username"] == "dev-principal"
            assert conf["sasl.password"] == _CREDENTIAL_MARKER

    def test_unauthenticated_transport_failure_says_the_lane_declared_no_security(
        self,
    ) -> None:
        from omnibase_core.cli.cli_run_node import publish_and_poll
        from omnibase_core.errors import OnexError

        consumer = MagicMock()
        consumer.list_topics.side_effect = RuntimeError(
            "KafkaError{code=_TRANSPORT,val=-195,str=Broker transport failure}"
        )
        with (
            patch(_PATCH_TOPIC_PARTITION, side_effect=_FakeTopicPartition),
            patch(_PATCH_PRODUCER, return_value=MagicMock()),
            patch(_PATCH_CONSUMER, return_value=consumer),
        ):
            with pytest.raises(OnexError) as exc_info:
                publish_and_poll(
                    node_id="node_dod_verify",
                    payload={},
                    timeout=5,
                    bootstrap_servers="redpanda:9092",
                    command_topic="onex.cmd.test.command.v1",
                    response_topic="onex.evt.test.completed.v1",
                )
        assert "declares no security protocol" in str(exc_info.value)

    def test_transport_failure_with_sasl_never_prints_the_password(self) -> None:
        from omnibase_core.cli.cli_run_node import publish_and_poll
        from omnibase_core.errors import OnexError

        consumer = MagicMock()
        consumer.list_topics.side_effect = RuntimeError("_TRANSPORT")
        with (
            patch(_PATCH_TOPIC_PARTITION, side_effect=_FakeTopicPartition),
            patch(_PATCH_PRODUCER, return_value=MagicMock()),
            patch(_PATCH_CONSUMER, return_value=consumer),
        ):
            with pytest.raises(OnexError) as exc_info:
                publish_and_poll(
                    node_id="node_dod_verify",
                    payload={},
                    timeout=5,
                    bootstrap_servers="redpanda:9092",
                    command_topic="onex.cmd.test.command.v1",
                    response_topic="onex.evt.test.completed.v1",
                    client_security=kafka_binding(
                        sasl_password=_CREDENTIAL_MARKER
                    ).client_security(),
                )
        message = str(exc_info.value)
        assert "security.protocol=SASL_PLAINTEXT" in message
        assert _CREDENTIAL_MARKER not in message
