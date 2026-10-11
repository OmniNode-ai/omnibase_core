#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Thin publisher for the house routing-overlay write command.

Operator entry point for node_house_routing_overlay_effect: reads one command
as JSON (a declare or a retire), validates it as
ModelHouseRoutingOverlayCommand, and publishes the bare command (no envelope)
to the node's command topic. The topic is read from the node's contract.yaml,
never hardcoded. Nothing is published unless the command validates. The command
cannot name a tenant: the node writes the house tenant only.

Usage:
    uv run python -m omnimarket.nodes.node_house_routing_overlay_effect.publish_house_overlay_command \
        --command command.json \
        (--bootstrap-servers <host:port> | --dry-run)

Kafka: --bootstrap-servers plus the SASL variables the shared auth helper reads.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Protocol

import yaml
from pydantic import ValidationError

from omnimarket.nodes.node_house_routing_overlay_effect.models.model_house_routing_overlay import (
    ModelHouseRoutingOverlayCommand,
)

_CONTRACT = Path(__file__).resolve().parent / "contract.yaml"


class ProtocolCommandProducer(Protocol):
    def send(self, topic: str, value: dict[str, object]) -> None: ...


def command_topic() -> str:
    contract = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    topic = contract["runtime_dispatch"]["command_topic"]
    if topic not in contract["event_bus"]["subscribe_topics"]:
        raise SystemExit(f"{topic} is not a subscribe topic of {_CONTRACT}")
    return str(topic)


def build_command(text: str) -> ModelHouseRoutingOverlayCommand:
    try:
        return ModelHouseRoutingOverlayCommand.model_validate(json.loads(text))
    except (ValidationError, ValueError) as exc:
        raise SystemExit(f"house overlay command is invalid: {exc}") from None


def publish_command(text: str, producer: ProtocolCommandProducer) -> int:
    command = build_command(text)
    producer.send(command_topic(), command.model_dump(mode="json"))
    return 1


class _KafkaProducer:
    """Buffers sends, then flushes them in one async session."""

    def __init__(self, bootstrap: str) -> None:
        self._bootstrap = bootstrap
        self._pending: list[tuple[str, dict[str, object]]] = []

    def send(self, topic: str, value: dict[str, object]) -> None:
        self._pending.append((topic, value))

    async def flush(self) -> None:
        from aiokafka import AIOKafkaProducer
        from omnibase_infra.event_bus.kafka_auth import (
            build_aiokafka_auth_kwargs_from_env,
        )

        producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            **build_aiokafka_auth_kwargs_from_env(),
        )
        await producer.start()
        try:
            for topic, value in self._pending:
                await producer.send_and_wait(topic, value=value)
        finally:
            await producer.stop()


class _DryRunProducer:
    def send(self, topic: str, value: dict[str, object]) -> None:
        sys.stdout.write(json.dumps({"topic": topic, "value": value}) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--command", required=True, help="JSON file, one command")
    parser.add_argument(
        "--bootstrap-servers", default="", help="Kafka bootstrap servers"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    text = Path(args.command).read_text(encoding="utf-8")
    if args.dry_run:
        count = publish_command(text, _DryRunProducer())
    else:
        if not args.bootstrap_servers:
            parser.error("--bootstrap-servers is required unless --dry-run")
        kafka = _KafkaProducer(args.bootstrap_servers)
        count = publish_command(text, kafka)
        asyncio.run(kafka.flush())
    sys.stderr.write(f"published {count} house-overlay command(s)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
