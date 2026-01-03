"""
Protocol for Event Bus Listener operations.

This protocol defines the duck-typed interface for event bus operations
used by the event listener mixin.
"""

from collections.abc import Callable
from typing import Protocol, runtime_checkable

__all__ = ["ProtocolEventBusListener"]


@runtime_checkable
class ProtocolEventBusListener(Protocol):
    """Protocol for event bus used by MixinEventListener.

    This protocol defines the duck-typed interface for event bus operations
    used by the event listener mixin. It is runtime_checkable to support
    hasattr() checks before method calls.
    """

    def subscribe(self, handler: Callable[..., object], event_type: str) -> object:
        """Subscribe to events with a handler."""
        ...

    def unsubscribe(self, subscription: object) -> None:
        """Unsubscribe from events."""
        ...

    async def publish_async(self, envelope: object) -> object:
        """Asynchronous publish method."""
        ...
