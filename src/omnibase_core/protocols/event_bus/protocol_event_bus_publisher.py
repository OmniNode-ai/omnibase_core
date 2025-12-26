"""
Protocol for event bus publishing operations (ISP - Interface Segregation Principle).

This module provides the ProtocolEventBusPublisher protocol definition
for components that only need to publish events, without requiring
the full ProtocolEventBus interface.

Design Principles:
- Minimal interface: Only publishing-related methods
- Runtime checkable: Supports duck typing with @runtime_checkable
- ISP compliant: Components that only publish don't need subscribe/lifecycle methods
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from omnibase_core.protocols.base import ContextValue
from omnibase_core.protocols.event_bus.protocol_event_bus_headers import (
    ProtocolEventBusHeaders,
)

if TYPE_CHECKING:
    from omnibase_core.protocols.event_bus.protocol_event_envelope import (
        ProtocolEventEnvelope,
    )


@runtime_checkable
class ProtocolEventBusPublisher(Protocol):
    """
    Protocol for event bus publishing operations.

    This is a minimal interface for components that only need to publish events.
    It follows the Interface Segregation Principle (ISP) by separating
    publishing concerns from subscription and lifecycle management.

    Use Cases:
    - Nodes that emit events but don't consume them
    - Effect nodes publishing results to downstream consumers
    - Services that only need fire-and-forget messaging

    Example:
        >>> class MyPublisher:
        ...     def __init__(self, publisher: ProtocolEventBusPublisher):
        ...         self.publisher = publisher
        ...
        ...     async def emit_event(self, data: bytes) -> None:
        ...         await self.publisher.publish("my.topic", None, data)
    """

    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: ProtocolEventBusHeaders | None = None,
    ) -> None:
        """
        Publish a raw message to a topic.

        Args:
            topic: The topic to publish to.
            key: Optional message key for partitioning.
            value: The message payload as bytes.
            headers: Optional message headers.

        Raises:
            OnexError: If publishing fails (connection error, serialization, etc.).
        """
        ...

    async def publish_envelope(
        self,
        envelope: ProtocolEventEnvelope[object],
        topic: str,
    ) -> None:
        """
        Publish an event envelope to a topic.

        This is a higher-level method that handles envelope serialization
        and metadata extraction automatically.

        Args:
            envelope: The event envelope to publish.
            topic: The topic to publish to.

        Raises:
            OnexError: If publishing fails.
        """
        ...

    async def broadcast_to_environment(
        self,
        command: str,
        payload: dict[str, ContextValue],
        target_environment: str | None = None,
    ) -> None:
        """
        Broadcast a command to all nodes in an environment.

        Args:
            command: The command identifier.
            payload: Command payload data.
            target_environment: Target environment (uses current if None).
        """
        ...

    async def send_to_group(
        self,
        command: str,
        payload: dict[str, ContextValue],
        target_group: str,
    ) -> None:
        """
        Send a command to a specific node group.

        Args:
            command: The command identifier.
            payload: Command payload data.
            target_group: The target node group.
        """
        ...


__all__ = ["ProtocolEventBusPublisher"]
