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

    This protocol provides two publish methods with different semantics:

    - ``publish``: Primary async publish method. Awaits until the event
      is accepted by the event bus (but not necessarily delivered to subscribers).
      Use this for standard async publishing where you need confirmation
      the event was accepted.

    - ``publish_async``: Fire-and-forget async publish. Schedules the event
      for publishing without waiting for acceptance confirmation.
      Use this when you want to minimize latency and can tolerate
      potential event loss on failures.

    Both methods are async to support non-blocking I/O, but they differ
    in their delivery guarantees and error handling behavior.

    Example:
        >>> bus: ProtocolAsyncEventBus = get_event_bus()
        >>> # Standard publish - waits for acceptance
        >>> await bus.publish(event)
        >>> # Fire-and-forget - returns immediately
        >>> await bus.publish_async(event)
    """

    async def publish(self, event: ProtocolEventMessage) -> None:
        """
        Publish an event and wait for acceptance confirmation.

        This method awaits until the event bus confirms acceptance of the event.
        It provides stronger delivery guarantees compared to ``publish_async``.

        Args:
            event: The event message to publish. Must conform to
                ProtocolEventMessage.

        Raises:
            OnexError: If the event cannot be accepted by the event bus
                (e.g., connection failure, serialization error).

        Note:
            "Accepted" means the event bus has received and queued the event,
            not that subscribers have processed it. For end-to-end delivery
            confirmation, use acknowledgment patterns at the application level.
        """
        ...

    async def publish_async(self, event: ProtocolEventMessage) -> None:
        """
        Publish an event without waiting for acceptance confirmation.

        This is a fire-and-forget method that schedules the event for
        publishing and returns immediately. Use this when you prioritize
        low latency over delivery guarantees.

        Args:
            event: The event message to publish. Must conform to
                ProtocolEventMessage.

        Note:
            This method may not raise exceptions for transient failures.
            Events may be silently dropped if the event bus is unavailable.
            Use ``publish`` if you need confirmation that the event was accepted.

        Warning:
            Do not use this method for critical events where delivery
            must be confirmed. Use ``publish`` instead.
        """
        ...


__all__ = ["ProtocolAsyncEventBus"]
