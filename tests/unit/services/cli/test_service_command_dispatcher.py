#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for CommandDispatcher — OMN-2553.

Covers:
    - KAFKA_EVENT: successful dispatch publishes to correct topic
    - KAFKA_EVENT: correlation ID is returned and is a valid UUID
    - KAFKA_EVENT: fire-and-forget (no exception on success)
    - KAFKA_EVENT: Kafka produce error captured in result (success=False)
    - KAFKA_EVENT: no producer configured raises CommandDispatchError
    - KAFKA_EVENT: empty topic raises CommandDispatchError
    - required field validation: missing required arg returns error result
    - required field validation: all required fields present → dispatch proceeds
    - unsupported types: HTTP_ENDPOINT, DIRECT_CALL, SUBPROCESS raise error
    - ModelCommandDispatchResult.to_json: valid JSON with expected keys
    - ModelCommandDispatchResult frozen: immutable after construction
"""

from __future__ import annotations

import json
import uuid
from argparse import Namespace
from typing import Any

import pytest

from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility
from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType
from omnibase_core.errors.error_command_dispatch import CommandDispatchError
from omnibase_core.models.cli.model_command_dispatch_result import (
    ModelCommandDispatchResult,
)
from omnibase_core.models.contracts.model_cli_contribution import (
    ModelCliCommandEntry,
    ModelCliInvocation,
)
from omnibase_core.services.cli.service_command_dispatcher import CommandDispatcher

# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------


class _FakeKafkaProducer:
    """In-memory stub for KafkaProducerProtocol."""

    def __init__(self, *, fail_on_produce: bool = False) -> None:
        self.produced: list[dict[str, Any]] = []
        self.fail_on_produce = fail_on_produce
        self.flushed = False

    def produce(self, topic: str, key: str, value: bytes) -> None:
        if self.fail_on_produce:
            raise RuntimeError("Kafka broker unreachable")
        self.produced.append({"topic": topic, "key": key, "value": value})

    def flush(self, timeout: float = 5.0) -> None:
        self.flushed = True


def _make_command(
    invocation_type: EnumCliInvocationType = EnumCliInvocationType.KAFKA_EVENT,
    topic: str = "onex.cmd.test.v1",
    cmd_id: str = "com.omninode.test.run",
) -> ModelCliCommandEntry:
    invocation = ModelCliInvocation(
        invocation_type=invocation_type,
        topic=topic if invocation_type == EnumCliInvocationType.KAFKA_EVENT else None,
        endpoint=(
            "http://localhost:8080/test"
            if invocation_type == EnumCliInvocationType.HTTP_ENDPOINT
            else None
        ),
        callable_ref=(
            "omnibase_core.test.callable"
            if invocation_type == EnumCliInvocationType.DIRECT_CALL
            else None
        ),
        subprocess_cmd=(
            "echo test" if invocation_type == EnumCliInvocationType.SUBPROCESS else None
        ),
    )
    return ModelCliCommandEntry(
        id=cmd_id,
        display_name="Test Run",
        description="Run a test command.",
        group="test",
        args_schema_ref="com.omninode.test.run.args.v1",
        output_schema_ref="com.omninode.test.run.output.v1",
        invocation=invocation,
        risk=EnumCliCommandRisk.LOW,
        visibility=EnumCliCommandVisibility.PUBLIC,
    )


def _make_namespace(**kwargs: Any) -> Namespace:
    return Namespace(**kwargs)


# ---------------------------------------------------------------------------
# Tests: KAFKA_EVENT dispatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_kafka_dispatch_success() -> None:
    """Successful KAFKA_EVENT dispatch returns success=True."""
    producer = _FakeKafkaProducer()
    dispatcher = CommandDispatcher(kafka_producer=producer)
    command = _make_command()
    ns = _make_namespace(mode="fast", limit=5, json=False)

    result = dispatcher.dispatch(command, ns)

    assert result.success is True
    assert result.command_ref == "com.omninode.test.run"
    assert result.topic == "onex.cmd.test.v1"
    assert result.error_message is None


@pytest.mark.unit
def test_kafka_dispatch_produces_to_correct_topic() -> None:
    """Dispatch publishes to the topic specified in the command invocation."""
    producer = _FakeKafkaProducer()
    dispatcher = CommandDispatcher(kafka_producer=producer)
    command = _make_command(topic="onex.cmd.memory.query.v1")
    ns = _make_namespace(query="hello", json=False)

    dispatcher.dispatch(command, ns)

    assert len(producer.produced) == 1
    assert producer.produced[0]["topic"] == "onex.cmd.memory.query.v1"


@pytest.mark.unit
def test_kafka_dispatch_returns_valid_uuid_correlation_id() -> None:
    """Dispatch result correlation_id is a valid UUID4 string."""
    producer = _FakeKafkaProducer()
    dispatcher = CommandDispatcher(kafka_producer=producer)
    result = dispatcher.dispatch(_make_command(), _make_namespace(json=False))

    parsed = uuid.UUID(result.correlation_id)
    assert parsed.version == 4


@pytest.mark.unit
def test_kafka_dispatch_correlation_id_in_payload() -> None:
    """Correlation ID is embedded in the Kafka message payload."""
    producer = _FakeKafkaProducer()
    dispatcher = CommandDispatcher(kafka_producer=producer)
    result = dispatcher.dispatch(_make_command(), _make_namespace(json=False))

    payload = json.loads(producer.produced[0]["value"])
    assert payload["correlation_id"] == result.correlation_id


@pytest.mark.unit
def test_kafka_dispatch_flushes_producer() -> None:
    """Dispatcher calls flush() after produce()."""
    producer = _FakeKafkaProducer()
    dispatcher = CommandDispatcher(kafka_producer=producer)
    dispatcher.dispatch(_make_command(), _make_namespace(json=False))

    assert producer.flushed is True


@pytest.mark.unit
def test_kafka_dispatch_produce_failure_returns_error_result() -> None:
    """A Kafka produce exception is captured as success=False result."""
    producer = _FakeKafkaProducer(fail_on_produce=True)
    dispatcher = CommandDispatcher(kafka_producer=producer)
    result = dispatcher.dispatch(_make_command(), _make_namespace(json=False))

    assert result.success is False
    assert result.error_message is not None
    assert "Kafka produce failed" in result.error_message


@pytest.mark.unit
def test_kafka_dispatch_no_producer_raises() -> None:
    """Dispatching KAFKA_EVENT with no producer raises CommandDispatchError."""
    dispatcher = CommandDispatcher(kafka_producer=None)
    with pytest.raises(CommandDispatchError, match="No Kafka producer"):
        dispatcher.dispatch(_make_command(), _make_namespace(json=False))


@pytest.mark.unit
def test_kafka_dispatch_empty_topic_raises() -> None:
    """A KAFKA_EVENT command with empty topic raises CommandDispatchError."""
    # Build a command with a KAFKA_EVENT invocation but no topic by bypassing validator.
    invocation = ModelCliInvocation.__new__(ModelCliInvocation)
    object.__setattr__(invocation, "invocation_type", EnumCliInvocationType.KAFKA_EVENT)
    object.__setattr__(invocation, "topic", "")
    object.__setattr__(invocation, "endpoint", None)
    object.__setattr__(invocation, "callable_ref", None)
    object.__setattr__(invocation, "subprocess_cmd", None)

    command = ModelCliCommandEntry.__new__(ModelCliCommandEntry)
    object.__setattr__(command, "id", "com.omninode.test.empty-topic")
    object.__setattr__(command, "display_name", "Empty Topic")
    object.__setattr__(command, "description", "Test.")
    object.__setattr__(command, "group", "test")
    object.__setattr__(command, "args_schema_ref", "ref.v1")
    object.__setattr__(command, "output_schema_ref", "ref.v1")
    object.__setattr__(command, "invocation", invocation)
    object.__setattr__(command, "permissions", [])
    object.__setattr__(command, "risk", EnumCliCommandRisk.LOW)
    object.__setattr__(command, "requires_hitl", False)
    object.__setattr__(command, "visibility", EnumCliCommandVisibility.PUBLIC)
    object.__setattr__(command, "examples", [])

    producer = _FakeKafkaProducer()
    dispatcher = CommandDispatcher(kafka_producer=producer)
    with pytest.raises(CommandDispatchError, match="topic is empty"):
        dispatcher.dispatch(command, _make_namespace(json=False))


# ---------------------------------------------------------------------------
# Tests: stub invocation types
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_http_endpoint_raises_dispatch_error() -> None:
    """HTTP_ENDPOINT invocation raises CommandDispatchError (stub)."""
    dispatcher = CommandDispatcher()
    command = _make_command(invocation_type=EnumCliInvocationType.HTTP_ENDPOINT)
    with pytest.raises(CommandDispatchError, match="HTTP_ENDPOINT"):
        dispatcher.dispatch(command, _make_namespace(json=False))


@pytest.mark.unit
def test_direct_call_raises_dispatch_error() -> None:
    """DIRECT_CALL invocation raises CommandDispatchError (stub)."""
    dispatcher = CommandDispatcher()
    command = _make_command(invocation_type=EnumCliInvocationType.DIRECT_CALL)
    with pytest.raises(CommandDispatchError, match="DIRECT_CALL"):
        dispatcher.dispatch(command, _make_namespace(json=False))


@pytest.mark.unit
def test_subprocess_raises_dispatch_error() -> None:
    """SUBPROCESS invocation raises CommandDispatchError (stub)."""
    dispatcher = CommandDispatcher()
    command = _make_command(invocation_type=EnumCliInvocationType.SUBPROCESS)
    with pytest.raises(CommandDispatchError, match="SUBPROCESS"):
        dispatcher.dispatch(command, _make_namespace(json=False))


# ---------------------------------------------------------------------------
# Tests: pre-dispatch required-field validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_required_field_missing_returns_error_result() -> None:
    """dispatch() returns error result when a required schema field is absent."""
    schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "description": "Mode."},
        },
        "required": ["mode"],
    }
    producer = _FakeKafkaProducer()
    dispatcher = CommandDispatcher(kafka_producer=producer)
    command = _make_command()
    # Namespace without 'mode'
    ns = _make_namespace(limit=5, json=False)

    result = dispatcher.dispatch(command, ns, args_schema=schema)

    assert result.success is False
    assert result.error_message is not None
    assert "--mode" in result.error_message
    # Kafka should NOT have been called.
    assert len(producer.produced) == 0


@pytest.mark.unit
def test_required_field_present_dispatches_successfully() -> None:
    """dispatch() proceeds when all required fields are present."""
    schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "description": "Mode."},
        },
        "required": ["mode"],
    }
    producer = _FakeKafkaProducer()
    dispatcher = CommandDispatcher(kafka_producer=producer)
    command = _make_command()
    ns = _make_namespace(mode="fast", json=False)

    result = dispatcher.dispatch(command, ns, args_schema=schema)

    assert result.success is True
    assert len(producer.produced) == 1


@pytest.mark.unit
def test_no_schema_skips_validation() -> None:
    """When args_schema is None, required field validation is skipped."""
    producer = _FakeKafkaProducer()
    dispatcher = CommandDispatcher(kafka_producer=producer)
    command = _make_command()
    # No required field provided — but no schema, so no error.
    ns = _make_namespace(json=False)

    result = dispatcher.dispatch(command, ns, args_schema=None)

    assert result.success is True


# ---------------------------------------------------------------------------
# Tests: ModelCommandDispatchResult
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dispatch_result_to_json_valid() -> None:
    """ModelCommandDispatchResult.to_json() returns parseable JSON with expected keys."""
    result = ModelCommandDispatchResult(
        success=True,
        correlation_id=str(uuid.uuid4()),
        command_ref="com.omninode.test.run",
        invocation_type=EnumCliInvocationType.KAFKA_EVENT,
        topic="onex.cmd.test.v1",
    )
    parsed = json.loads(result.to_json())
    assert parsed["success"] is True
    assert "correlation_id" in parsed
    assert parsed["command_ref"] == "com.omninode.test.run"
    assert parsed["invocation_type"] == "kafka_event"
    assert parsed["topic"] == "onex.cmd.test.v1"
    assert "dispatched_at" in parsed


@pytest.mark.unit
def test_dispatch_result_is_frozen() -> None:
    """ModelCommandDispatchResult is immutable after construction."""
    result = ModelCommandDispatchResult(
        success=True,
        correlation_id=str(uuid.uuid4()),
        command_ref="com.omninode.test.run",
        invocation_type=EnumCliInvocationType.KAFKA_EVENT,
    )
    with pytest.raises((AttributeError, TypeError)):
        result.success = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: end-to-end schema → parser → dispatch cycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_end_to_end_schema_parse_and_dispatch() -> None:
    """Integration: parse args from schema then dispatch to Kafka."""
    from omnibase_core.services.cli.service_schema_argument_parser import (
        SchemaArgumentParser,
    )

    schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "limit": {"type": "integer", "description": "Max results.", "default": 10},
        },
        "required": ["query"],
    }
    command = _make_command(cmd_id="com.omninode.memory.search")

    # Phase 1: parse args from schema.
    parser = SchemaArgumentParser.from_schema(
        command_id=command.id,
        display_name="Memory Search",
        description="Search the memory store.",
        args_schema=schema,
    )
    ns = parser.parse_args(["--query", "hello world", "--limit", "5"])
    assert ns.query == "hello world"
    assert ns.limit == 5

    # Phase 2: dispatch.
    producer = _FakeKafkaProducer()
    dispatcher = CommandDispatcher(kafka_producer=producer)
    result = dispatcher.dispatch(command, ns, args_schema=schema)

    assert result.success is True
    payload = json.loads(producer.produced[0]["value"])
    assert payload["args"]["query"] == "hello world"
    assert payload["args"]["limit"] == 5
