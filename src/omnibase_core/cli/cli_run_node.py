# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex run-node`` — publish a command to Kafka and poll for the result."""

from __future__ import annotations

import importlib
import json
import os
import sys
import time
import uuid

import click

from omnibase_core.constants.constants_event_types import (
    TOPIC_CLI_RUN_NODE_CMD,
    TOPIC_CLI_RUN_NODE_RESPONSE,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


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
) -> dict[str, object] | None:
    """Publish a command envelope to onex.cmd and poll for a correlated response.

    Returns the response dict, or None on timeout.
    """
    try:
        _ck = importlib.import_module("confluent_kafka")
        # NOTE(OMN-9715): lazy importlib import preserves ADR-005 transport boundary; attr-defined suppressed because confluent_kafka stubs are incomplete
        Producer = _ck.Producer  # type: ignore[attr-defined]
        Consumer = _ck.Consumer  # type: ignore[attr-defined]
    except ImportError as exc:
        raise ModelOnexError(
            code=EnumCoreErrorCode.IMPORT_ERROR,
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
                    code=EnumCoreErrorCode.RUNTIME_ERROR,
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
        consumer.subscribe([TOPIC_CLI_RUN_NODE_RESPONSE])
        while not consumer.assignment():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ModelOnexError(
                    code=EnumCoreErrorCode.RUNTIME_ERROR,
                    message="Timed out waiting for Kafka consumer partition assignment",
                )
            consumer.poll(timeout=min(remaining, 0.1))

        producer = Producer({"bootstrap.servers": bootstrap_servers})
        producer.produce(
            topic=TOPIC_CLI_RUN_NODE_CMD,
            value=json.dumps(envelope).encode(),
            on_delivery=_on_delivery,
        )
        pending = producer.flush(timeout=10.0)
        if pending:
            raise ModelOnexError(
                code=EnumCoreErrorCode.RUNTIME_ERROR,
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

    Publishes a command envelope to the onex.cmd topic with the given NODE_ID
    and input payload, then polls for a correlated response. Exits non-zero
    on failure or timeout, emitting a SkillRoutingError JSON envelope.
    """
    try:
        payload = json.loads(input_json)
    except json.JSONDecodeError as exc:
        _emit_error(node_id, f"Invalid JSON input: {exc}")

    bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")

    try:
        response = publish_and_poll(
            node_id=node_id,
            payload=payload,
            timeout=timeout,
            bootstrap_servers=bootstrap_servers,
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
