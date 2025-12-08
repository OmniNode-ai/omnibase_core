"""
Protocol for event message objects in the event bus.

This module provides the ProtocolEventMessage protocol definition for
event-driven messaging in the ONEX architecture.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolEventMessage(Protocol):
    """
    Protocol for event message objects in the event bus.

    Represents a message that can be published to and received from
    the event bus, with acknowledgment support.
    """

    @property
    def topic(self) -> str:
        """Get the topic this message was published to."""
        ...

    @property
    def key(self) -> bytes | None:
        """Get the message key."""
        ...

    @property
    def value(self) -> bytes:
        """Get the message value."""
        ...

    @property
    def headers(self) -> dict[str, str]:
        """Get the message headers."""
        ...

    async def ack(self) -> None:
        """Acknowledge the message."""
        ...

    async def nack(self) -> None:
        """Negatively acknowledge the message."""
        ...


__all__ = ["ProtocolEventMessage"]
