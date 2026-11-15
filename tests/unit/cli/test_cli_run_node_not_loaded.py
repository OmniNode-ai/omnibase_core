# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-24561: ``onex run-node`` refuses immediately when no runtime consumer serves the command topic.

Before this fix a node not loaded in the bus's runtime swallowed the request:
the command was published to a topic nobody consumed, and the CLI spent its
whole ``--timeout`` before printing a Timeout error. The command now takes one
bounded admin read before publishing (``read_runtime_consumer_state``) and refuses
— typed, immediate, nothing sent — only on positive evidence: the caller can
see the runtime's consumer groups and none of them is bound to the command
topic. Every incomplete outcome (unreachable broker, listing error, rebalancing
group, runtime groups invisible to this caller) fails open to ``"unknown"`` and
the dispatch proceeds exactly as before.
"""

from __future__ import annotations

import json
import sys
import types
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from tests.unit.cli.node_broker_fixtures import RESOLVER_PATCH_TARGET, kafka_binding

pytestmark = pytest.mark.unit

_STATE_PATCH_TARGET = (
    "omnibase_core.handlers.handler_run_node_consumer_state.read_runtime_consumer_state"
)
_TOPICS_PATCH_TARGET = "omnibase_core.cli.cli_run_node._resolve_node_topics"
_PUBLISH_PATCH_TARGET = "omnibase_core.cli.cli_run_node.publish_and_poll"
_COMMAND_TOPIC = "onex.cmd.omn24561.node-start.v1"
_TERMINAL_TOPIC = "onex.evt.omn24561.node-completed.v1"
_TOPIC_GROUP = f"onex-dev.svc.node.consume.v1.__t.{_COMMAND_TOPIC}"
_OTHER_TOPIC_GROUP = "onex-dev.svc.node.consume.v1.__t.onex.cmd.omn24561.other.v1"
_TIMEOUT_S = 2.5
_CLI_GROUP = "onex-dev.omnibase_core.cli_run_node.consume.v1.__i.9f2c0000-0000-4000-8000-000000000000"


class _FakeFuture:
    """The ``.result(timeout=...)`` slice of the admin futures."""

    def __init__(self, result: object = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error

    def result(self, timeout: float | None = None) -> object:
        if self._error is not None:
            raise self._error
        return self._result


class _FakeGroupListing:
    def __init__(self, group_id: str) -> None:
        self.group_id = group_id


class _FakeListResult:
    def __init__(
        self,
        valid: list[_FakeGroupListing] | None = None,
        errors: list[Exception] | None = None,
    ) -> None:
        self.valid = valid or []
        self.errors = errors or []


class _FakeTopicPartition:
    def __init__(self, topic: str, partition: int = 0) -> None:
        self.topic = topic
        self.partition = partition


class _FakeMember:
    def __init__(self, topics: list[str]) -> None:
        self.assignment = types.SimpleNamespace(
            topic_partitions=[_FakeTopicPartition(topic) for topic in topics]
        )


class _FakeGroupDescription:
    """``state`` is a str or an enum-like object exposing ``.name``."""

    def __init__(self, state: object, members: list[_FakeMember] | None = None) -> None:
        self.state = state
        self.members = members or []


class _FakeAdminClient:
    """The slice of ``confluent_kafka.admin.AdminClient`` the loaded check reads.

    A ``descriptions`` value may be an Exception: that group's describe future
    raises instead of resolving.
    """

    def __init__(
        self,
        conf: dict[str, object],
        list_result: _FakeListResult | None = None,
        list_error: Exception | None = None,
        descriptions: dict[str, object] | None = None,
    ) -> None:
        self.conf = conf
        self.describe_calls: list[list[str]] = []
        self._list_result = list_result
        self._list_error = list_error
        self._descriptions = descriptions or {}

    def list_consumer_groups(self, request_timeout: float | None = None) -> _FakeFuture:
        if self._list_error is not None:
            return _FakeFuture(error=self._list_error)
        return _FakeFuture(result=self._list_result)

    def describe_consumer_groups(
        self, group_ids: list[str], request_timeout: float | None = None
    ) -> dict[str, _FakeFuture]:
        self.describe_calls.append(list(group_ids))
        futures: dict[str, _FakeFuture] = {}
        for group_id in group_ids:
            outcome = self._descriptions[group_id]
            if isinstance(outcome, Exception):
                futures[group_id] = _FakeFuture(error=outcome)
            else:
                futures[group_id] = _FakeFuture(result=outcome)
        return futures


class _FakeKafkaException(Exception):
    """Stands in for confluent_kafka.KafkaException."""


def _fake_admin_modules(
    list_result: _FakeListResult | None = None,
    list_error: Exception | None = None,
    descriptions: dict[str, object] | None = None,
) -> dict[str, types.ModuleType]:
    """sys.modules entries that make importlib.import_module resolve the fake."""

    def _admin_client(conf: dict[str, object]) -> _FakeAdminClient:
        return _FakeAdminClient(
            conf,
            list_result=list_result,
            list_error=list_error,
            descriptions=descriptions,
        )

    admin_module = types.ModuleType("confluent_kafka.admin")
    admin_module.AdminClient = _admin_client
    confluent_module = types.ModuleType("confluent_kafka")
    confluent_module.admin = admin_module
    confluent_module.KafkaException = _FakeKafkaException
    return {
        "confluent_kafka": confluent_module,
        "confluent_kafka.admin": admin_module,
    }


def _check_state(
    list_result: _FakeListResult | None = None,
    list_error: Exception | None = None,
    descriptions: dict[str, object] | None = None,
) -> str:
    """``read_runtime_consumer_state`` against a fake confluent_kafka.admin."""
    from omnibase_core.handlers.handler_run_node_consumer_state import (
        read_runtime_consumer_state,
    )

    with patch.dict(
        sys.modules, _fake_admin_modules(list_result, list_error, descriptions)
    ):
        return read_runtime_consumer_state(
            "redpanda:19092",
            {"security.protocol": "PLAINTEXT"},
            _COMMAND_TOPIC,
            _TIMEOUT_S,
        )


class TestRuntimeConsumerState:
    """The verdict machine: exactly one of serving / not_loaded / unknown."""

    def test_the_marker_is_the_consumer_group_topic_scope_infix(self) -> None:
        from omnibase_core.event_bus.util_consumer_group import TOPIC_SCOPE_INFIX

        assert TOPIC_SCOPE_INFIX == ".__t."

    def test_not_loaded_when_no_runtime_group_serves_the_command_topic(
        self,
    ) -> None:
        assert (
            _check_state(
                list_result=_FakeListResult(
                    valid=[
                        _FakeGroupListing(_OTHER_TOPIC_GROUP),
                        _FakeGroupListing(_CLI_GROUP),
                    ]
                )
            )
            == "not_loaded"
        )

    def test_serving_when_a_stable_group_member_holds_the_topic(self) -> None:
        assert (
            _check_state(
                list_result=_FakeListResult(valid=[_FakeGroupListing(_TOPIC_GROUP)]),
                descriptions={
                    _TOPIC_GROUP: _FakeGroupDescription(
                        "Stable", [_FakeMember([_COMMAND_TOPIC])]
                    )
                },
            )
            == "serving"
        )

    def test_serving_when_the_state_is_an_enum_like_name(self) -> None:
        # confluent_kafka describes groups with a ConsumerGroupState enum whose
        # .name is e.g. "STABLE"; the check must read .name when it is there.
        assert (
            _check_state(
                list_result=_FakeListResult(valid=[_FakeGroupListing(_TOPIC_GROUP)]),
                descriptions={
                    _TOPIC_GROUP: _FakeGroupDescription(
                        types.SimpleNamespace(name="STABLE"),
                        [_FakeMember([_COMMAND_TOPIC])],
                    )
                },
            )
            == "serving"
        )

    def test_not_loaded_when_a_stable_group_holds_no_partition_of_the_topic(
        self,
    ) -> None:
        assert (
            _check_state(
                list_result=_FakeListResult(valid=[_FakeGroupListing(_TOPIC_GROUP)]),
                descriptions={
                    _TOPIC_GROUP: _FakeGroupDescription(
                        "Stable", [_FakeMember(["onex.cmd.omn24561.elsewhere.v1"])]
                    )
                },
            )
            == "not_loaded"
        )

    def test_not_loaded_when_the_topic_group_is_empty(self) -> None:
        assert (
            _check_state(
                list_result=_FakeListResult(valid=[_FakeGroupListing(_TOPIC_GROUP)]),
                descriptions={_TOPIC_GROUP: _FakeGroupDescription("Empty")},
            )
            == "not_loaded"
        )

    def test_unknown_when_no_runtime_group_is_visible(self) -> None:
        assert (
            _check_state(
                list_result=_FakeListResult(valid=[_FakeGroupListing(_CLI_GROUP)])
            )
            == "unknown"
        )

    def test_unknown_when_the_listing_has_errors(self) -> None:
        assert (
            _check_state(
                list_result=_FakeListResult(
                    valid=[_FakeGroupListing(_TOPIC_GROUP)],
                    errors=[RuntimeError("LISTENER authorization denied")],
                )
            )
            == "unknown"
        )

    def test_unknown_when_the_listing_raises(self) -> None:
        assert (
            _check_state(
                list_error=RuntimeError(
                    "KafkaError{code=_TRANSPORT,val=-195,str=Broker transport failure}"
                )
            )
            == "unknown"
        )

    def test_unknown_when_confluent_kafka_is_not_installed(self) -> None:
        from omnibase_core.handlers.handler_run_node_consumer_state import (
            read_runtime_consumer_state,
        )

        with patch.dict(
            sys.modules, {"confluent_kafka": None, "confluent_kafka.admin": None}
        ):
            assert (
                read_runtime_consumer_state(
                    "redpanda:19092",
                    {"security.protocol": "PLAINTEXT"},
                    _COMMAND_TOPIC,
                    _TIMEOUT_S,
                )
                == "unknown"
            )

    def test_unknown_when_a_topic_group_is_not_stable(self) -> None:
        # A rebalancing group is mid-flight evidence; it must not refuse.
        assert (
            _check_state(
                list_result=_FakeListResult(valid=[_FakeGroupListing(_TOPIC_GROUP)]),
                descriptions={
                    _TOPIC_GROUP: _FakeGroupDescription(
                        "preparing_rebalance", [_FakeMember([_COMMAND_TOPIC])]
                    )
                },
            )
            == "unknown"
        )

    def test_unknown_when_the_describe_future_raises(self) -> None:
        assert (
            _check_state(
                list_result=_FakeListResult(valid=[_FakeGroupListing(_TOPIC_GROUP)]),
                descriptions={_TOPIC_GROUP: RuntimeError("describe timed out")},
            )
            == "unknown"
        )

    def test_admin_client_gets_the_binding_transport_and_security(self) -> None:
        from omnibase_core.handlers.handler_run_node_consumer_state import (
            read_runtime_consumer_state,
        )

        created: list[_FakeAdminClient] = []

        def _admin_client(conf: dict[str, object]) -> _FakeAdminClient:
            client = _FakeAdminClient(conf, list_result=_FakeListResult())
            created.append(client)
            return client

        entries = _fake_admin_modules()
        entries["confluent_kafka.admin"].AdminClient = _admin_client
        with patch.dict(sys.modules, entries):
            assert (
                read_runtime_consumer_state(
                    "redpanda:19092",
                    {
                        "security.protocol": "SASL_PLAINTEXT",
                        "sasl.mechanism": "SCRAM-SHA-256",
                    },
                    _COMMAND_TOPIC,
                    _TIMEOUT_S,
                )
                == "unknown"
            )
        assert created[0].conf == {
            "bootstrap.servers": "redpanda:19092",
            "security.protocol": "SASL_PLAINTEXT",
            "sasl.mechanism": "SCRAM-SHA-256",
        }

    def test_confluent_kafka_not_imported_at_module_level(self) -> None:
        import importlib

        saved = sys.modules.pop("confluent_kafka", None)
        try:
            importlib.reload(importlib.import_module("omnibase_core.cli.cli_run_node"))
            assert "confluent_kafka" not in sys.modules, (
                "confluent_kafka must not be imported at module level in cli_run_node"
            )
        finally:
            if saved is not None:
                sys.modules["confluent_kafka"] = saved


class TestRunNodeNotLoadedRefusal:
    """The click command: typed refusal, exit 1, nothing published."""

    def test_not_loaded_refuses_without_publishing(self) -> None:
        from omnibase_core.cli.cli_run_node import run_node

        with (
            patch(RESOLVER_PATCH_TARGET, return_value=kafka_binding()),
            patch(
                _TOPICS_PATCH_TARGET,
                return_value=("/tmp/c.yaml", _COMMAND_TOPIC, _TERMINAL_TOPIC, False),
            ),
            patch(_STATE_PATCH_TARGET, return_value="not_loaded"),
            patch(_PUBLISH_PATCH_TARGET) as dial,
        ):
            result = CliRunner().invoke(run_node, ["node_x", "--input", "{}"])

        assert result.exit_code == 1
        envelope = json.loads(result.output)
        assert envelope["error_type"] == "SkillRoutingError"
        assert envelope["refusal"] == "node_not_loaded"
        assert envelope["command_topic"] == _COMMAND_TOPIC
        assert envelope["node_id"] == "node_x"
        assert f"No runtime consumer serves {_COMMAND_TOPIC}" in envelope["message"]
        assert "not loaded in the runtime of this bus" in envelope["message"]
        assert "nothing was sent" in envelope["message"]
        dial.assert_not_called()

    def test_serving_control_publishes(self) -> None:
        from omnibase_core.cli.cli_run_node import run_node

        with (
            patch(RESOLVER_PATCH_TARGET, return_value=kafka_binding()),
            patch(
                _TOPICS_PATCH_TARGET,
                return_value=("/tmp/c.yaml", _COMMAND_TOPIC, _TERMINAL_TOPIC, False),
            ),
            patch(_STATE_PATCH_TARGET, return_value="serving"),
            patch(
                _PUBLISH_PATCH_TARGET, return_value={"payload": {"status": "ok"}}
            ) as dial,
        ):
            result = CliRunner().invoke(run_node, ["node_x", "--input", "{}"])

        assert result.exit_code == 0
        assert json.loads(result.output) == {"status": "ok"}
        dial.assert_called_once()

    def test_unknown_fails_open_and_publishes(self) -> None:
        from omnibase_core.cli.cli_run_node import run_node

        with (
            patch(RESOLVER_PATCH_TARGET, return_value=kafka_binding()),
            patch(
                _TOPICS_PATCH_TARGET,
                return_value=("/tmp/c.yaml", _COMMAND_TOPIC, _TERMINAL_TOPIC, False),
            ),
            patch(_STATE_PATCH_TARGET, return_value="unknown"),
            patch(
                _PUBLISH_PATCH_TARGET, return_value={"payload": {"status": "ok"}}
            ) as dial,
        ):
            result = CliRunner().invoke(run_node, ["node_x", "--input", "{}"])

        assert result.exit_code == 0
        dial.assert_called_once()
