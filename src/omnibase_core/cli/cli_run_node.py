# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex run-node`` — dispatch a packaged node over Kafka using its contract."""

from __future__ import annotations

import importlib
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import NoReturn
from uuid import UUID

import click

from omnibase_core.cli.cli_node import _resolve_packaged_contract
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.runtime.runtime_local import load_workflow_contract


def _emit_error(node_id: str, message: str, **extra: str | int) -> NoReturn:
    """Emit a SkillRoutingError JSON envelope and exit non-zero."""
    envelope: dict[str, str | int] = {
        "error_type": "SkillRoutingError",
        "message": message,
        "node_id": node_id,
        **extra,
    }
    click.echo(json.dumps(envelope, indent=2))
    sys.exit(1)


def _contract_requires_payload_correlation_id(contract: dict[str, object]) -> bool:
    """Return True when the contract explicitly requires payload.correlation_id."""
    inputs = contract.get("inputs")
    if not isinstance(inputs, dict):
        return False

    correlation_spec = inputs.get("correlation_id")
    if not isinstance(correlation_spec, dict):
        return False

    return correlation_spec.get("required") is True


def _resolve_node_topics(node_id: str) -> tuple[Path, str, str, bool]:
    """Resolve a packaged node to its contract path and Kafka routing metadata."""
    contract_path = _resolve_packaged_contract(node_id)
    contract = load_workflow_contract(contract_path)

    event_bus = contract.get("event_bus")
    if not isinstance(event_bus, dict):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=(
                f"Node '{node_id}' contract at {contract_path} is missing an "
                "event_bus mapping"
            ),
        )

    subscribe_topics = event_bus.get("subscribe_topics")
    if not isinstance(subscribe_topics, list) or not subscribe_topics:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=(
                f"Node '{node_id}' contract at {contract_path} does not declare "
                "event_bus.subscribe_topics"
            ),
        )

    command_topic = subscribe_topics[0]
    if not isinstance(command_topic, str) or not command_topic.strip():
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=(
                f"Node '{node_id}' contract at {contract_path} has an invalid "
                "primary subscribe topic"
            ),
        )

    terminal_event = contract.get("terminal_event")
    if not isinstance(terminal_event, str) or not terminal_event.strip():
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=(
                f"Node '{node_id}' contract at {contract_path} does not declare "
                "a terminal_event"
            ),
        )

    return (
        contract_path,
        command_topic,
        terminal_event,
        _contract_requires_payload_correlation_id(contract),
    )


def _normalize_payload(
    payload: dict[str, object],
    correlation_id: UUID,
    inject_payload_correlation_id: bool,
) -> dict[str, object]:
    """Ensure the payload carries a correlation_id for input models that require one."""
    normalized = dict(payload)
    if inject_payload_correlation_id and normalized.get("correlation_id") in (None, ""):
        normalized["correlation_id"] = str(correlation_id)
    return normalized


def publish_and_poll(
    node_id: str,
    payload: dict[str, object],
    timeout: int,
    bootstrap_servers: str,
    command_topic: str,
    response_topic: str,
    inject_payload_correlation_id: bool = False,
) -> dict[str, object] | None:
    """Publish a contract-routed command envelope and poll for its terminal event.

    Returns the response dict, or None on timeout.
    """
    try:
        _ck = importlib.import_module("confluent_kafka")
        # NOTE(OMN-9715): lazy importlib import preserves ADR-005 transport boundary; attr-defined suppressed because confluent_kafka stubs are incomplete
        Producer = _ck.Producer  # type: ignore[attr-defined]
        Consumer = _ck.Consumer  # type: ignore[attr-defined]
        OFFSET_END = _ck.OFFSET_END  # type: ignore[attr-defined]
        TopicPartition = _ck.TopicPartition  # type: ignore[attr-defined]
    except ImportError as exc:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.IMPORT_ERROR,
            message=(
                "confluent-kafka is required for run-node. "
                "Install with: uv add omnibase-core[kafka]"
            ),
        ) from exc

    correlation_uuid = uuid.uuid4()
    correlation_id = str(correlation_uuid)
    normalized_payload = _normalize_payload(
        payload,
        correlation_uuid,
        inject_payload_correlation_id,
    )
    envelope = ModelEventEnvelope[object](
        payload=normalized_payload,
        correlation_id=correlation_uuid,
        source_tool="onex.run-node",
        target_tool=node_id,
    )

    delivery_error: list[Exception] = []

    def _on_delivery(err: object, _msg: object) -> None:
        if err is not None:
            delivery_error.append(
                ModelOnexError(
                    error_code=EnumCoreErrorCode.RUNTIME_ERROR,
                    message=f"Kafka delivery failed: {err}",
                )
            )

    deadline = time.monotonic() + timeout
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": f"onex-run-node-{correlation_id}",
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
    )
    try:
        # Explicit assignment is more reliable than ephemeral group rebalances
        # for one-shot request/response flows.
        metadata = consumer.list_topics(response_topic, timeout=10.0)
        topic_metadata = metadata.topics.get(response_topic)
        if topic_metadata is None or getattr(topic_metadata, "error", None) is not None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.RUNTIME_ERROR,
                message=f"Kafka topic metadata unavailable for {response_topic}",
            )

        response_partitions: list[object] = []
        for partition_id in sorted(topic_metadata.partitions):
            response_partitions.append(
                TopicPartition(response_topic, partition_id, OFFSET_END)
            )

        if not response_partitions:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.RUNTIME_ERROR,
                message=f"Kafka topic {response_topic} has no partitions",
            )

        consumer.assign(response_partitions)

        producer = Producer({"bootstrap.servers": bootstrap_servers})
        producer.produce(
            topic=command_topic,
            value=envelope.model_dump_json().encode(),
            on_delivery=_on_delivery,
        )
        pending = producer.flush(timeout=10.0)
        if pending:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.RUNTIME_ERROR,
                message=f"Kafka flush timed out with {pending} queued message(s)",
            )

        if delivery_error:
            raise delivery_error[0]

        while True:
            now = time.monotonic()
            remaining = deadline - now
            if remaining <= 0:
                break
            msg = consumer.poll(timeout=min(remaining, 1.0))
            if msg is None:
                continue
            if msg.error():
                continue
            raw = msg.value()
            if raw is None:
                continue
            try:
                data: dict[str, object] = json.loads(raw.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if data.get("correlation_id") == correlation_id:
                return data
    finally:
        consumer.close()

    return None


@click.command("run-node")
@click.argument("node_id")
@click.option(
    "--input",
    "input_json",
    required=True,
    help="JSON payload to send to the node.",
)
@click.option(
    "--timeout",
    type=int,
    default=30,
    show_default=True,
    help="Max seconds to wait for a response.",
)
def run_node(node_id: str, input_json: str, timeout: int) -> None:
    """Execute a remote ONEX node via Kafka.

    Resolves NODE_ID via the packaged contract.yaml, publishes a command envelope
    to the node's primary subscribe topic, and polls its declared terminal_event.
    Exits non-zero on failure or timeout, emitting a SkillRoutingError JSON
    envelope.
    """
    try:
        payload = json.loads(input_json)
    except json.JSONDecodeError as exc:
        _emit_error(node_id, f"Invalid JSON input: {exc}")

    bootstrap_servers = os.environ["KAFKA_BOOTSTRAP_SERVERS"]

    try:
        (
            _contract_path,
            command_topic,
            response_topic,
            inject_payload_correlation_id,
        ) = _resolve_node_topics(node_id)
        response = publish_and_poll(
            node_id=node_id,
            payload=payload,
            timeout=timeout,
            bootstrap_servers=bootstrap_servers,
            command_topic=command_topic,
            response_topic=response_topic,
            inject_payload_correlation_id=inject_payload_correlation_id,
        )
    except (ConnectionError, OSError, ImportError, ModelOnexError) as exc:
        _emit_error(node_id, str(exc))

    if response is None:
        _emit_error(
            node_id,
            f"Timeout after {timeout}s waiting for response from {node_id}",
            timeout_seconds=timeout,
        )

    click.echo(json.dumps(response.get("payload", response), indent=2))
