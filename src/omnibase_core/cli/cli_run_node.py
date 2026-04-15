# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex run-node`` — publish a command to Kafka and poll for the result."""

from __future__ import annotations

import json
import os
import sys
import time
import uuid

import click


def publish_and_poll(
    node_id: str,
    payload: dict,
    timeout: int,
    bootstrap_servers: str,
) -> dict | None:
    """Publish a command envelope to onex.cmd and poll for a correlated response.

    Returns the response dict, or None on timeout.
    """
    try:
        from kafka import KafkaConsumer, KafkaProducer
    except ImportError as exc:
        raise ImportError(
            "kafka-python is required for run-node. "
            "Install with: pip install kafka-python-ng"
        ) from exc

    correlation_id = str(uuid.uuid4())
    response_topic = "onex.cmd.response"

    envelope = {
        "correlation_id": correlation_id,
        "node_id": node_id,
        "payload": payload,
        "timestamp": time.time(),
    }

    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    producer.send("onex.cmd", value=envelope)
    producer.flush()
    producer.close()

    consumer = KafkaConsumer(
        response_topic,
        bootstrap_servers=bootstrap_servers,
        value_deserializer=lambda v: json.loads(v.decode()),
        auto_offset_reset="latest",
        consumer_timeout_ms=timeout * 1000,
        group_id=f"onex-run-node-{correlation_id}",
    )

    deadline = time.monotonic() + timeout
    try:
        for message in consumer:
            if message.value.get("correlation_id") == correlation_id:
                return message.value
            if time.monotonic() > deadline:
                return None
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
        error = {
            "error_type": "SkillRoutingError",
            "message": f"Invalid JSON input: {exc}",
            "node_id": node_id,
        }
        click.echo(json.dumps(error, indent=2))
        sys.exit(1)

    bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")

    try:
        response = publish_and_poll(
            node_id=node_id,
            payload=payload,
            timeout=timeout,
            bootstrap_servers=bootstrap_servers,
        )
    except (ConnectionError, OSError, ImportError) as exc:
        error = {
            "error_type": "SkillRoutingError",
            "message": str(exc),
            "node_id": node_id,
        }
        click.echo(json.dumps(error, indent=2))
        sys.exit(1)

    if response is None:
        error = {
            "error_type": "SkillRoutingError",
            "message": f"Timeout after {timeout}s waiting for response from {node_id}",
            "node_id": node_id,
            "timeout_seconds": timeout,
        }
        click.echo(json.dumps(error, indent=2))
        sys.exit(1)

    click.echo(json.dumps(response, indent=2))
