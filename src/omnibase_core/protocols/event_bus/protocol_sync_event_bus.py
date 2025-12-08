"""
Protocol for synchronous event bus operations.

This module provides the ProtocolSyncEventBus protocol definition
for synchronous event bus implementations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.protocols.event_bus.protocol_event_message import (
    ProtocolEventMessage,
)


@runtime_checkable
class ProtocolSyncEventBus(Protocol):
    """
    Protocol for synchronous event bus operations.

    Defines synchronous event publishing interface for event bus
    implementations that operate synchronously.
    """

    async def publish(self, event: ProtocolEventMessage) -> None:
        """Publish an event asynchronously."""
        ...

    async def publish_sync(self, event: ProtocolEventMessage) -> None:
        """Publish an event synchronously."""
        ...


__all__ = ["ProtocolSyncEventBus"]
