"""
Base protocol for event bus operations.

This module provides the ProtocolEventBusBase protocol definition
for common event bus operations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.protocols.event_bus.protocol_event_message import (
    ProtocolEventMessage,
)


@runtime_checkable
class ProtocolEventBusBase(Protocol):
    """
    Base protocol for event bus operations.

    Defines common event publishing interface that both synchronous
    and asynchronous event buses must implement.
    """

    async def publish(self, event: ProtocolEventMessage) -> None:
        """Publish an event."""
        ...


__all__ = ["ProtocolEventBusBase"]
