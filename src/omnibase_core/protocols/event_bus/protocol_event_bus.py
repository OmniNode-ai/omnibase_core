"""
ONEX event bus protocol for distributed messaging infrastructure.

This module provides the ProtocolEventBus protocol definition
for the main event bus interface.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from omnibase_core.protocols.base import ContextValue
from omnibase_core.protocols.event_bus.protocol_event_bus_headers import (
    ProtocolEventBusHeaders,
)
from omnibase_core.protocols.event_bus.protocol_event_message import (
    ProtocolEventMessage,
)
from omnibase_core.protocols.event_bus.protocol_kafka_event_bus_adapter import (
    ProtocolKafkaEventBusAdapter,
)


@runtime_checkable
class ProtocolEventBus(Protocol):
    """
    ONEX event bus protocol for distributed messaging infrastructure.

    Implements the ONEX Messaging Design with environment isolation
    and node group mini-meshes.
    """

    @property
    def adapter(self) -> ProtocolKafkaEventBusAdapter:
        """Get the underlying adapter."""
        ...

    @property
    def environment(self) -> str:
        """Get the environment (dev, staging, prod)."""
        ...

    @property
    def group(self) -> str:
        """Get the node group."""
        ...

    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: ProtocolEventBusHeaders | None = None,
    ) -> None:
        """Publish a message to a topic."""
        ...

    async def subscribe(
        self,
        topic: str,
        group_id: str,
        on_message: Callable[[ProtocolEventMessage], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        """Subscribe to a topic."""
        ...

    async def broadcast_to_environment(
        self,
        command: str,
        payload: dict[str, ContextValue],
        target_environment: str | None = None,
    ) -> None:
        """Broadcast a command to all nodes in an environment."""
        ...

    async def send_to_group(
        self, command: str, payload: dict[str, ContextValue], target_group: str
    ) -> None:
        """Send a command to a specific node group."""
        ...

    async def close(self) -> None:
        """Close the event bus."""
        ...


__all__ = ["ProtocolEventBus"]
