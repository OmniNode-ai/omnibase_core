# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex run-node`` — publish a command to Kafka and poll for the result."""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import json
import os
import sys
import time
import uuid
from pathlib import Path

import click
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model


def _resolve_node_topics(node_id: str) -> tuple[str, str]:
    """Resolve the cmd and response topics for a node from its contract.yaml.

    Returns (cmd_topic, response_topic).  Looks up the node via the
    ``onex.nodes`` entry-point group, loads the colocated contract.yaml,
    and reads:
      - cmd_topic:      event_bus.subscribe_topics[0]
      - response_topic: terminal_event

    Raises click.ClickException if the node is unknown, the contract is
    missing, or the required fields are absent.
    """

    class _EventBus(BaseModel):  # type: ignore[explicit-any]
        model_config = ConfigDict(extra="ignore")
        subscribe_topics: list[str] = Field(default_factory=list)

    class _ContractTopics(BaseModel):  # type: ignore[explicit-any]
        model_config = ConfigDict(extra="ignore")
        event_bus: _EventBus = Field(default_factory=_EventBus)
        terminal_event: str = ""

    matches = [
        ep
        for ep in importlib.metadata.entry_points(group="onex.nodes")
        if ep.name == node_id
    ]
    if not matches:
        known = sorted(
            {ep.name for ep in importlib.metadata.entry_points(group="onex.nodes")}
        )
        raise click.ClickException(
            f"Unknown node '{node_id}'. Known nodes: {', '.join(known) or '(none)'}"
        )
    if len(matches) > 1:
        sources = ", ".join(str(ep.dist) for ep in matches)
        raise click.ClickException(
            f"Duplicate entry-point '{node_id}' registered by: {sources}"
        )

    module_path = matches[0].value.split(":", 1)[0].strip()
    spec = importlib.util.find_spec(module_path)
    if spec is None:
        raise click.ClickException(
            f"Failed to resolve module '{module_path}' for node '{node_id}'"
        )

    if spec.submodule_search_locations:
        module_dir = Path(next(iter(spec.submodule_search_locations))).resolve()
    elif spec.origin is not None:
        module_dir = Path(spec.origin).resolve().parent
    else:
        raise click.ClickException(
            f"Node '{node_id}' module '{module_path}' has no origin; "
            "cannot locate contract.yaml"
        )

    contract_path = module_dir / "contract.yaml"
    if not contract_path.exists():
        raise click.ClickException(
            f"Node '{node_id}' has no contract.yaml at {contract_path}"
        )

    try:
        contract = load_and_validate_yaml_model(contract_path, _ContractTopics)
    except ModelOnexError as exc:
        raise click.ClickException(
            f"Node '{node_id}' contract.yaml failed to load: {exc.message}"
        )

    if not contract.event_bus.subscribe_topics:
        raise click.ClickException(
            f"Node '{node_id}' contract.yaml has no event_bus.subscribe_topics; "
            "cannot determine which Kafka topic to publish the command to"
        )
    cmd_topic = contract.event_bus.subscribe_topics[0]

    if not contract.terminal_event:
        raise click.ClickException(
            f"Node '{node_id}' contract.yaml has no terminal_event; "
            "cannot determine which Kafka topic to poll for the response"
        )

    return cmd_topic, contract.terminal_event


def _emit_error(node_id: str, message: str, **extra: str | int) -> None:
    """Emit a SkillRoutingError JSON envelope and exit non-zero."""
    envelope: dict[str, str | int] = {
        "error_type": "SkillRoutingError",
        "message": message,
        "node_id": node_id,
        **extra,
    }
    click.echo(json.dumps(envelope, indent=2))
    sys.exit(1)


def publish_and_poll(
    node_id: str,
    payload: dict[str, object],
    timeout: int,
    bootstrap_servers: str,
    cmd_topic: str,
    response_topic: str,
) -> dict[str, object] | None:
    """Publish a command envelope to cmd_topic and poll response_topic for a result.

    Returns the response dict, or None on timeout.
    """
    try:
        _ck = importlib.import_module("confluent_kafka")
        # NOTE(OMN-9715): lazy importlib import preserves ADR-005 transport boundary; attr-defined suppressed because confluent_kafka stubs are incomplete
        Producer = _ck.Producer  # type: ignore[attr-defined]
        Consumer = _ck.Consumer  # type: ignore[attr-defined]
    except ImportError as exc:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.IMPORT_ERROR,
            message=(
                "confluent-kafka is required for run-node. "
                "Install with: uv add omnibase-core[kafka]"
            ),
        ) from exc

    correlation_id = str(uuid.uuid4())

    envelope = {
        "correlation_id": correlation_id,
        "node_id": node_id,
        "payload": payload,
        "timestamp": time.time(),
    }

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
        # Subscribe and wait for partition assignment before producing.
        # subscribe() is asynchronous — assignment only happens during poll().
        # Waiting here (within the caller's deadline) ensures a fast responder
        # cannot produce the reply before this consumer holds partitions
        # (auto.offset.reset="latest" would skip any pre-assignment messages).
        consumer.subscribe([response_topic])
        while not consumer.assignment():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.RUNTIME_ERROR,
                    message="Timed out waiting for Kafka consumer partition assignment",
                )
            consumer.poll(timeout=min(remaining, 0.1))

        producer = Producer({"bootstrap.servers": bootstrap_servers})
        producer.produce(
            topic=cmd_topic,
            value=json.dumps(envelope).encode(),
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

    Resolves the node's contract-declared input and terminal topics, publishes
    a command envelope, then polls for a correlated response. Exits non-zero
    on failure or timeout, emitting a SkillRoutingError JSON envelope.
    """
    try:
        payload = json.loads(input_json)
    except json.JSONDecodeError as exc:
        _emit_error(node_id, f"Invalid JSON input: {exc}")

    try:
        cmd_topic, response_topic = _resolve_node_topics(node_id)
    except click.ClickException as exc:
        _emit_error(node_id, exc.format_message())

    bootstrap_servers = os.environ["KAFKA_BOOTSTRAP_SERVERS"]

    try:
        response = publish_and_poll(
            node_id=node_id,
            payload=payload,
            timeout=timeout,
            bootstrap_servers=bootstrap_servers,
            cmd_topic=cmd_topic,
            response_topic=response_topic,
        )
    except (ConnectionError, OSError, ImportError, ModelOnexError) as exc:
        _emit_error(node_id, str(exc))

    if response is None:
        _emit_error(
            node_id,
            f"Timeout after {timeout}s waiting for response from {node_id}",
            timeout_seconds=timeout,
        )

    click.echo(json.dumps(response, indent=2))
