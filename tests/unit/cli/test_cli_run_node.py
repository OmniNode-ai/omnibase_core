# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for cli_run_node — confluent_kafka producer/consumer path (OMN-9715)."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

pytestmark = pytest.mark.unit

# Producer and Consumer are imported inside publish_and_poll (lazy import), so
# patch them at their source — confluent_kafka.Producer / confluent_kafka.Consumer.
_PATCH_PRODUCER = "confluent_kafka.Producer"
_PATCH_CONSUMER = "confluent_kafka.Consumer"


def _make_mock_message(
    correlation_id: str, extra: dict[str, object] | None = None
) -> MagicMock:
    msg = MagicMock()
    msg.error.return_value = None
    data: dict[str, object] = {"correlation_id": correlation_id, "status": "ok"}
    if extra:
        data.update(extra)
    msg.value.return_value = json.dumps(data).encode()
    return msg


def _make_assigned_consumer(
    config: dict[str, object] | None = None,
    poll_side_effect: object = None,
    poll_return_value: object = None,
) -> MagicMock:
    """Return a mock Consumer whose assignment() is truthy (already assigned)."""
    consumer = MagicMock()
    consumer.assignment.return_value = [object()]
    if poll_side_effect is not None:
        consumer.poll.side_effect = poll_side_effect
    elif poll_return_value is not None:
        consumer.poll.return_value = poll_return_value
    else:
        consumer.poll.return_value = None
    return consumer


class TestCliRunNodeNoKafkaPythonImport:
    """Assert that kafka-python (module ``kafka``) is NOT imported at module load time."""

    def test_kafka_python_not_imported_at_module_level(self) -> None:
        import importlib
        import importlib.util

        # Import symbols locally so the module-level import below doesn't affect this test
        spec = importlib.util.find_spec("omnibase_core.cli.cli_run_node")
        assert spec is not None
        # Verify the module itself does not trigger a kafka-python import on reload
        saved = sys.modules.pop("kafka", None)
        try:
            importlib.reload(importlib.import_module("omnibase_core.cli.cli_run_node"))
            assert "kafka" not in sys.modules, (
                "kafka-python must not be imported at module level in cli_run_node"
            )
        finally:
            if saved is not None:
                sys.modules["kafka"] = saved

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


_MOCK_CMD_TOPIC = "onex.cmd.test.node-start.v1"
_MOCK_RESPONSE_TOPIC = "onex.evt.test.node-completed.v1"
_PATCH_RESOLVE_TOPICS = "omnibase_core.cli.cli_run_node._resolve_node_topics"


class TestResolveNodeTopics:
    """Test _resolve_node_topics contract lookup (OMN-10511)."""

    def test_unknown_node_raises_click_exception(self) -> None:
        import click

        from omnibase_core.cli.cli_run_node import _resolve_node_topics

        with patch(
            "omnibase_core.cli.cli_run_node.importlib.metadata.entry_points",
            return_value=[],
        ):
            with pytest.raises(click.ClickException, match="Unknown node"):
                _resolve_node_topics("nonexistent-node")

    def test_duplicate_entry_point_raises_click_exception(self) -> None:
        import click

        from omnibase_core.cli.cli_run_node import _resolve_node_topics

        ep1 = MagicMock()
        ep1.name = "my-node"
        ep1.value = "pkg.nodes.my_node:MyNode"
        ep2 = MagicMock()
        ep2.name = "my-node"
        ep2.value = "other.nodes.my_node:MyNode"

        with patch(
            "omnibase_core.cli.cli_run_node.importlib.metadata.entry_points",
            return_value=[ep1, ep2],
        ):
            with pytest.raises(click.ClickException, match="Duplicate"):
                _resolve_node_topics("my-node")

    def test_resolves_topics_from_contract_yaml(self, tmp_path: Path) -> None:
        from omnibase_core.cli.cli_run_node import _resolve_node_topics

        contract = {
            "event_bus": {"subscribe_topics": [_MOCK_CMD_TOPIC]},
            "terminal_event": _MOCK_RESPONSE_TOPIC,
        }
        contract_file = tmp_path / "contract.yaml"
        import yaml as _yaml

        contract_file.write_text(_yaml.dump(contract))

        ep = MagicMock()
        ep.name = "my-node"
        ep.value = "pkg.nodes.my_node"

        mock_spec = MagicMock()
        mock_spec.submodule_search_locations = [str(tmp_path)]

        with (
            patch(
                "omnibase_core.cli.cli_run_node.importlib.metadata.entry_points",
                return_value=[ep],
            ),
            patch(
                "omnibase_core.cli.cli_run_node.importlib.util.find_spec",
                return_value=mock_spec,
            ),
        ):
            cmd_topic, response_topic = _resolve_node_topics("my-node")

        assert cmd_topic == _MOCK_CMD_TOPIC
        assert response_topic == _MOCK_RESPONSE_TOPIC

    def test_missing_subscribe_topics_raises(self, tmp_path: Path) -> None:
        import click
        import yaml as _yaml

        from omnibase_core.cli.cli_run_node import _resolve_node_topics

        contract = {"terminal_event": _MOCK_RESPONSE_TOPIC}
        (tmp_path / "contract.yaml").write_text(_yaml.dump(contract))

        ep = MagicMock()
        ep.name = "my-node"
        ep.value = "pkg.nodes.my_node"
        mock_spec = MagicMock()
        mock_spec.submodule_search_locations = [str(tmp_path)]

        with (
            patch(
                "omnibase_core.cli.cli_run_node.importlib.metadata.entry_points",
                return_value=[ep],
            ),
            patch(
                "omnibase_core.cli.cli_run_node.importlib.util.find_spec",
                return_value=mock_spec,
            ),
        ):
            with pytest.raises(click.ClickException, match="subscribe_topics"):
                _resolve_node_topics("my-node")

    def test_missing_terminal_event_raises(self, tmp_path: Path) -> None:
        import click
        import yaml as _yaml

        from omnibase_core.cli.cli_run_node import _resolve_node_topics

        contract = {"event_bus": {"subscribe_topics": [_MOCK_CMD_TOPIC]}}
        (tmp_path / "contract.yaml").write_text(_yaml.dump(contract))

        ep = MagicMock()
        ep.name = "my-node"
        ep.value = "pkg.nodes.my_node"
        mock_spec = MagicMock()
        mock_spec.submodule_search_locations = [str(tmp_path)]

        with (
            patch(
                "omnibase_core.cli.cli_run_node.importlib.metadata.entry_points",
                return_value=[ep],
            ),
            patch(
                "omnibase_core.cli.cli_run_node.importlib.util.find_spec",
                return_value=mock_spec,
            ),
        ):
            with pytest.raises(click.ClickException, match="terminal_event"):
                _resolve_node_topics("my-node")


class TestPublishAndPoll:
    """Test publish_and_poll with stubbed confluent_kafka Producer and Consumer."""

    def test_produce_call_shape(self) -> None:
        from omnibase_core.cli.cli_run_node import publish_and_poll

        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0  # all messages delivered
        mock_consumer = _make_assigned_consumer()

        # assign_deadline call → 1000, deadline call → 1000,
        # assignment wait: remaining>0, consumer.assignment() truthy → skip loop body
        # first poll-loop now → 1050 (remaining = -45, breaks immediately)
        _monotonic_values = iter([1000.0, 1000.0, 1050.0])

        with (
            patch(
                "omnibase_core.cli.cli_run_node.time.monotonic",
                side_effect=_monotonic_values,
            ),
            patch(
                "omnibase_core.cli.cli_run_node.time.time", return_value=1234567890.0
            ),
            patch(_PATCH_CONSUMER, return_value=mock_consumer),
            patch(_PATCH_PRODUCER, return_value=mock_producer),
        ):
            publish_and_poll(
                node_id="test-node",
                payload={"foo": "bar"},
                timeout=5,
                bootstrap_servers="localhost:19092",
                cmd_topic=_MOCK_CMD_TOPIC,
                response_topic=_MOCK_RESPONSE_TOPIC,
            )

        mock_producer.produce.assert_called_once()
        produce_kwargs = mock_producer.produce.call_args
        assert produce_kwargs.kwargs.get("topic") == _MOCK_CMD_TOPIC
        mock_consumer.subscribe.assert_called_once_with([_MOCK_RESPONSE_TOPIC])
        mock_producer.flush.assert_called_once_with(timeout=10.0)

    def test_returns_correlated_message(self) -> None:
        from omnibase_core.cli.cli_run_node import publish_and_poll

        original_uuid4 = __import__("uuid").uuid4

        corr_id_holder: list[str] = []

        def _capture_uuid4() -> object:
            uid = original_uuid4()
            corr_id_holder.append(str(uid))
            return uid

        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0  # all messages delivered

        def _make_consumer(config: dict[str, object]) -> MagicMock:
            consumer = MagicMock()
            group_id = str(config.get("group.id", ""))
            corr = group_id.removeprefix("onex-run-node-")
            msg = _make_mock_message(corr)
            consumer.poll.side_effect = [None, msg]
            consumer.assignment.return_value = [object()]
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
            # return_value so monotonic() never exhausts regardless of call count
            mock_time.monotonic.return_value = start

            result = publish_and_poll(
                node_id="my-node",
                payload={},
                timeout=30,
                bootstrap_servers="localhost:19092",
                cmd_topic=_MOCK_CMD_TOPIC,
                response_topic=_MOCK_RESPONSE_TOPIC,
            )

        assert result is not None
        assert result.get("status") == "ok"

    def test_returns_none_on_timeout(self) -> None:
        from omnibase_core.cli.cli_run_node import publish_and_poll

        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0  # all messages delivered
        mock_consumer = _make_assigned_consumer()

        # deadline call → 1000, first now → 1050 (remaining = -45, breaks)
        _monotonic_values = iter([1000.0, 1000.0, 1050.0])

        with (
            patch(
                "omnibase_core.cli.cli_run_node.time.monotonic",
                side_effect=_monotonic_values,
            ),
            patch(
                "omnibase_core.cli.cli_run_node.time.time", return_value=1234567890.0
            ),
            patch(_PATCH_CONSUMER, return_value=mock_consumer),
            patch(_PATCH_PRODUCER, return_value=mock_producer),
        ):
            result = publish_and_poll(
                node_id="my-node",
                payload={},
                timeout=30,
                bootstrap_servers="localhost:19092",
                cmd_topic=_MOCK_CMD_TOPIC,
                response_topic=_MOCK_RESPONSE_TOPIC,
            )

        assert result is None
        mock_consumer.close.assert_called_once()

    def test_consumer_closed_on_match(self) -> None:
        from omnibase_core.cli.cli_run_node import publish_and_poll

        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0  # all messages delivered
        captured_consumer: list[MagicMock] = []

        def _make_consumer(config: dict[str, object]) -> MagicMock:
            consumer = MagicMock()
            group_id = str(config.get("group.id", ""))
            corr = group_id.removeprefix("onex-run-node-")
            msg = _make_mock_message(corr)
            consumer.poll.return_value = msg
            consumer.assignment.return_value = [object()]
            captured_consumer.append(consumer)
            return consumer

        # deadline → 1000, first now → 999 (remaining=29>0, enters poll loop)
        _monotonic_values = iter([1000.0, 999.0])

        with (
            patch(
                "omnibase_core.cli.cli_run_node.time.monotonic",
                side_effect=_monotonic_values,
            ),
            patch(
                "omnibase_core.cli.cli_run_node.time.time", return_value=1234567890.0
            ),
            patch(_PATCH_CONSUMER, side_effect=_make_consumer),
            patch(_PATCH_PRODUCER, return_value=mock_producer),
        ):
            result = publish_and_poll(
                node_id="my-node",
                payload={},
                timeout=30,
                bootstrap_servers="localhost:19092",
                cmd_topic=_MOCK_CMD_TOPIC,
                response_topic=_MOCK_RESPONSE_TOPIC,
            )

        assert result is not None
        assert len(captured_consumer) == 1
        captured_consumer[0].close.assert_called_once()

    def test_flush_pending_raises_onerror(self) -> None:
        from omnibase_core.cli.cli_run_node import publish_and_poll
        from omnibase_core.errors import OnexError

        mock_producer = MagicMock()
        mock_producer.flush.return_value = 1  # simulates queued message timeout
        mock_consumer = _make_assigned_consumer()

        with (
            patch(_PATCH_PRODUCER, return_value=mock_producer),
            patch(_PATCH_CONSUMER, return_value=mock_consumer),
        ):
            with pytest.raises(OnexError, match="flush timed out"):
                publish_and_poll(
                    node_id="x",
                    payload={},
                    timeout=5,
                    bootstrap_servers="localhost:19092",
                    cmd_topic=_MOCK_CMD_TOPIC,
                    response_topic=_MOCK_RESPONSE_TOPIC,
                )
        mock_consumer.close.assert_called_once()

    def test_raises_onerror_when_confluent_kafka_missing(self) -> None:
        from omnibase_core.cli.cli_run_node import publish_and_poll
        from omnibase_core.errors import OnexError

        with patch.dict(sys.modules, {"confluent_kafka": None}):
            with pytest.raises(OnexError, match="confluent-kafka is required"):
                publish_and_poll(
                    node_id="x",
                    payload={},
                    timeout=5,
                    bootstrap_servers="localhost:19092",
                    cmd_topic=_MOCK_CMD_TOPIC,
                    response_topic=_MOCK_RESPONSE_TOPIC,
                )

    def test_delivery_failure_raises_onerror(self) -> None:
        from omnibase_core.cli.cli_run_node import publish_and_poll
        from omnibase_core.errors import OnexError

        def _make_failing_producer(config: dict[str, object]) -> MagicMock:
            producer = MagicMock()

            def _produce(**kwargs: object) -> None:
                on_delivery = kwargs.get("on_delivery")
                if callable(on_delivery):
                    on_delivery("simulated delivery error", None)

            producer.produce.side_effect = _produce
            return producer

        mock_consumer = _make_assigned_consumer()

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
                    cmd_topic=_MOCK_CMD_TOPIC,
                    response_topic=_MOCK_RESPONSE_TOPIC,
                )


class TestRunNodeCommand:
    """Test the click run-node command via CliRunner."""

    def test_invalid_json_exits_nonzero(self) -> None:
        from omnibase_core.cli.cli_run_node import run_node

        runner = CliRunner()
        with patch(
            _PATCH_RESOLVE_TOPICS, return_value=(_MOCK_CMD_TOPIC, _MOCK_RESPONSE_TOPIC)
        ):
            result = runner.invoke(run_node, ["test-node", "--input", "not-json"])
        assert result.exit_code != 0

    def test_timeout_response_exits_nonzero(self) -> None:
        from omnibase_core.cli.cli_run_node import run_node

        runner = CliRunner()
        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0  # all messages delivered
        mock_consumer = _make_assigned_consumer()

        # deadline → 1000, first now → 1050 (breaks immediately)
        _monotonic_values = iter([1000.0, 1050.0])

        with (
            patch.dict("os.environ", {"KAFKA_BOOTSTRAP_SERVERS": "testhost:19092"}),
            patch(
                _PATCH_RESOLVE_TOPICS,
                return_value=(_MOCK_CMD_TOPIC, _MOCK_RESPONSE_TOPIC),
            ),
            patch(
                "omnibase_core.cli.cli_run_node.time.monotonic",
                side_effect=_monotonic_values,
            ),
            patch(
                "omnibase_core.cli.cli_run_node.time.time", return_value=1234567890.0
            ),
            patch(_PATCH_CONSUMER, return_value=mock_consumer),
            patch(_PATCH_PRODUCER, return_value=mock_producer),
        ):
            result = runner.invoke(
                run_node, ["test-node", "--input", '{"x": 1}', "--timeout", "30"]
            )

        assert result.exit_code != 0
        output = json.loads(result.output)
        assert output["error_type"] == "SkillRoutingError"
        assert "Timeout" in output["message"]

    def test_publishes_to_contract_declared_topics(self) -> None:
        """run-node must use contract-declared topics, not hardcoded ones (OMN-10511)."""
        from omnibase_core.cli.cli_run_node import run_node

        runner = CliRunner()
        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0
        captured_consumer: list[MagicMock] = []

        def _make_consumer(config: dict[str, object]) -> MagicMock:
            consumer = MagicMock()
            group_id = str(config.get("group.id", ""))
            corr = group_id.removeprefix("onex-run-node-")
            msg = _make_mock_message(corr, extra={"result": "done"})
            consumer.poll.return_value = msg
            consumer.assignment.return_value = [object()]
            captured_consumer.append(consumer)
            return consumer

        _monotonic_values = iter([1000.0, 999.0])

        with (
            patch.dict("os.environ", {"KAFKA_BOOTSTRAP_SERVERS": "testhost:19092"}),
            patch(
                _PATCH_RESOLVE_TOPICS,
                return_value=(_MOCK_CMD_TOPIC, _MOCK_RESPONSE_TOPIC),
            ),
            patch(
                "omnibase_core.cli.cli_run_node.time.monotonic",
                side_effect=_monotonic_values,
            ),
            patch(
                "omnibase_core.cli.cli_run_node.time.time", return_value=1234567890.0
            ),
            patch(_PATCH_CONSUMER, side_effect=_make_consumer),
            patch(_PATCH_PRODUCER, return_value=mock_producer),
        ):
            result = runner.invoke(
                run_node, ["my-node", "--input", "{}", "--timeout", "30"]
            )

        assert result.exit_code == 0, result.output
        produce_call = mock_producer.produce.call_args
        assert produce_call.kwargs["topic"] == _MOCK_CMD_TOPIC
        assert captured_consumer[0].subscribe.call_args[0][0] == [_MOCK_RESPONSE_TOPIC]


class TestCliRunNodeNoKafkaPythonImportIsolated:
    """Verify kafka module isolation without top-level module import."""

    def test_kafka_python_not_imported_at_module_level(self) -> None:
        import importlib

        saved = sys.modules.pop("kafka", None)
        try:
            importlib.reload(importlib.import_module("omnibase_core.cli.cli_run_node"))
            assert "kafka" not in sys.modules, (
                "kafka-python must not be imported at module level in cli_run_node"
            )
        finally:
            if saved is not None:
                sys.modules["kafka"] = saved
