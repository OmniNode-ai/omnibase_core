"""
Protocol for asynchronous event bus operations.

This module provides the ProtocolAsyncEventBus protocol definition
for asynchronous event bus implementations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.protocols.event_bus.protocol_event_message import (
    ProtocolEventMessage,
)


@runtime_checkable
class ProtocolAsyncEventBus(Protocol):
    """
    Protocol for asynchronous event bus operations.

    Defines asynchronous event publishing interface for event bus
    implementations that operate asynchronously.
    """

    async def publish(self, event: ProtocolEventMessage) -> None:
        """Publish an event."""
        ...

    async def publish_async(self, event: ProtocolEventMessage) -> None:
        """Publish an event asynchronously."""
        ...


__all__ = ["ProtocolAsyncEventBus"]
