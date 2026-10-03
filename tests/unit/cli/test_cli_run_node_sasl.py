# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-17427: ``onex run-node`` authenticates to a SASL lane broker.

The .201 dev lane's broker requires SASL_PLAINTEXT with SCRAM-SHA-256. Every
container on that lane carries the standard ``KAFKA_SECURITY_PROTOCOL`` /
``KAFKA_SASL_*`` environment, but ``onex run-node`` built its consumer and
producer from ``bootstrap.servers`` alone. The broker closed the
unauthenticated connection and the command reported
``Kafka broker unreachable`` even inside a container that held the
credential. These tests pin the client security configuration to that
environment and keep the credential out of every error message.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

pytestmark = pytest.mark.unit

_PATCH_PRODUCER = "confluent_kafka.Producer"
_PATCH_CONSUMER = "confluent_kafka.Consumer"
_PATCH_TOPIC_PARTITION = "confluent_kafka.TopicPartition"
_CREDENTIAL_MARKER = "credential-marker-never-printed"

_SECURITY_ENV = (
    "KAFKA_SECURITY_PROTOCOL",
    "KAFKA_SASL_MECHANISM",
    "KAFKA_SASL_USERNAME",
    "KAFKA_SASL_PASSWORD",
)


@pytest.fixture
def clean_security_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in _SECURITY_ENV:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _set_scram_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KAFKA_SECURITY_PROTOCOL", "SASL_PLAINTEXT")
    monkeypatch.setenv("KAFKA_SASL_MECHANISM", "SCRAM-SHA-256")
    monkeypatch.setenv("KAFKA_SASL_USERNAME", "dev-principal")
    monkeypatch.setenv("KAFKA_SASL_PASSWORD", _CREDENTIAL_MARKER)


class _FakeTopicPartition:
    def __init__(self, topic: str, partition: int, offset: int | None = None) -> None:
        self.topic = topic
        self.partition = partition
        self.offset = offset


class TestResolveClientSecurityConfig:
    def test_no_security_env_adds_nothing(
        self, clean_security_env: pytest.MonkeyPatch
    ) -> None:
        from omnibase_core.cli.cli_run_node import _resolve_client_security_config

        assert _resolve_client_security_config("node_x") == {}

    def test_scram_env_maps_to_librdkafka_keys(
        self, clean_security_env: pytest.MonkeyPatch
    ) -> None:
        from omnibase_core.cli.cli_run_node import _resolve_client_security_config

        _set_scram_env(clean_security_env)
        assert _resolve_client_security_config("node_x") == {
            "security.protocol": "SASL_PLAINTEXT",
            "sasl.mechanism": "SCRAM-SHA-256",
            "sasl.username": "dev-principal",
            "sasl.password": _CREDENTIAL_MARKER,
        }

    def test_plaintext_protocol_is_stated_without_sasl_keys(
        self, clean_security_env: pytest.MonkeyPatch
    ) -> None:
        from omnibase_core.cli.cli_run_node import _resolve_client_security_config

        clean_security_env.setenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
        assert _resolve_client_security_config("node_x") == {
            "security.protocol": "PLAINTEXT"
        }

    @pytest.mark.parametrize("missing", ["KAFKA_SASL_USERNAME", "KAFKA_SASL_PASSWORD"])
    def test_sasl_protocol_without_credential_fails_fast(
        self, clean_security_env: pytest.MonkeyPatch, missing: str
    ) -> None:
        from omnibase_core.cli.cli_run_node import run_node

        _set_scram_env(clean_security_env)
        clean_security_env.delenv(missing)
        clean_security_env.setenv("KAFKA_BOOTSTRAP_SERVERS", "lane-host:19092")
        result = CliRunner().invoke(run_node, ["node_dod_verify", "--input", "{}"])
        assert result.exit_code == 1
        assert missing in result.output
        assert _CREDENTIAL_MARKER not in result.output


class TestRunNodeAuthenticates:
    def test_consumer_and_producer_carry_the_sasl_config(
        self, clean_security_env: pytest.MonkeyPatch
    ) -> None:
        from omnibase_core.cli.cli_run_node import (
            _resolve_client_security_config,
            publish_and_poll,
        )

        _set_scram_env(clean_security_env)
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
                    client_security=_resolve_client_security_config("node_dod_verify"),
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

    def test_unauthenticated_transport_failure_names_the_sasl_env(
        self, clean_security_env: pytest.MonkeyPatch
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
        assert "KAFKA_SECURITY_PROTOCOL" in str(exc_info.value)

    def test_transport_failure_with_sasl_never_prints_the_password(
        self, clean_security_env: pytest.MonkeyPatch
    ) -> None:
        from omnibase_core.cli.cli_run_node import (
            _resolve_client_security_config,
            publish_and_poll,
        )
        from omnibase_core.errors import OnexError

        _set_scram_env(clean_security_env)
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
                    client_security=_resolve_client_security_config("node_dod_verify"),
                )
        message = str(exc_info.value)
        assert "security.protocol=SASL_PLAINTEXT" in message
        assert _CREDENTIAL_MARKER not in message
