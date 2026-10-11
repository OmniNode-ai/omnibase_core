# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Kafka publisher for the CI relay service.

Publishes PRStatusEvent instances to the configured Kafka bootstrap servers.
Uses aiokafka for async publishing within the FastAPI event loop.

The publisher is initialized lazily on first use and cleaned up on
application shutdown.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any  # any-ok: external API boundary

from omniclaude.services.ci_relay.models import PRStatusEvent

logger = logging.getLogger(__name__)

# Lazy-initialized producer (typed as Any because aiokafka is optional)
_producer: Any = None  # ONEX_EXCLUDE: any_type - external/untyped API boundary


def _get_bootstrap_servers() -> str:
    """Get Kafka bootstrap servers from environment.

    Returns:
        Bootstrap server string from KAFKA_BOOTSTRAP_SERVERS env var.

    Raises:
        RuntimeError: If KAFKA_BOOTSTRAP_SERVERS is not set.
    """
    servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "").strip()
    if not servers:
        raise RuntimeError(
            "KAFKA_BOOTSTRAP_SERVERS is not set. "
            "No localhost default to prevent silent local connections. [OMN-7227]"
        )
    return servers


async def _get_producer() -> (
    Any  # ONEX_EXCLUDE: any_type - external/untyped API boundary
):  # ONEX_EXCLUDE: any_type - external/untyped API boundary
    """Get or create the Kafka producer.

    Returns:
        An initialized AIOKafkaProducer instance.

    Raises:
        ImportError: If aiokafka is not installed.
    """
    global _producer
    if _producer is None:
        try:
            from aiokafka import AIOKafkaProducer

            _producer = AIOKafkaProducer(
                bootstrap_servers=_get_bootstrap_servers(),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                request_timeout_ms=5000,
                acks="all",
            )
            await _producer.start()
            logger.info("Kafka producer started: %s", _get_bootstrap_servers())
        except ImportError:
            logger.error("aiokafka not installed. Install with: uv add aiokafka")
            raise
    return _producer


async def publish_event(topic: str, event: PRStatusEvent) -> None:
    """Publish a PRStatusEvent to a Kafka topic.

    Args:
        topic: Kafka topic name.
        event: The event to publish.

    Raises:
        Exception: If publishing fails after producer initialization.
    """
    producer = await _get_producer()
    # Partition by repo for ordering guarantees per-repo
    partition_key = event.repo
    value = event.model_dump(mode="json")

    await producer.send_and_wait(
        topic,
        value=value,
        key=partition_key,
    )
    logger.debug(
        "Published to %s: key=%s message_id=%s",
        topic,
        partition_key,
        event.message_id,
    )


async def close_producer() -> None:
    """Close the Kafka producer. Call on application shutdown."""
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None
        logger.info("Kafka producer closed")
