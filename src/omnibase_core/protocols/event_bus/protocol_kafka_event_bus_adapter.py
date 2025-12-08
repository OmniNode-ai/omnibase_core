"""
Protocol for Event Bus Adapters supporting pluggable Kafka/Redpanda backends.

This module provides the ProtocolKafkaEventBusAdapter protocol definition
for pluggable messaging backend support.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from omnibase_core.protocols.event_bus.protocol_event_bus_headers import (
    ProtocolEventBusHeaders,
)
from omnibase_core.protocols.event_bus.protocol_event_message import (
    ProtocolEventMessage,
)


@runtime_checkable
class ProtocolKafkaEventBusAdapter(Protocol):
    """
    Protocol for Event Bus Adapters supporting pluggable Kafka/Redpanda backends.

    Implements the ONEX Messaging Design enabling drop-in support for
    both Kafka and Redpanda without code changes.
    """

    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: ProtocolEventBusHeaders,
    ) -> None:
        """Publish a message to a topic."""
        ...

    async def subscribe(
        self,
        topic: str,
        group_id: str,
        on_message: Callable[[ProtocolEventMessage], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        """
        Subscribe to a topic.

        Returns an unsubscribe function.
        """
        ...

    async def close(self) -> None:
        """Close the adapter connection."""
        ...


__all__ = ["ProtocolKafkaEventBusAdapter"]
