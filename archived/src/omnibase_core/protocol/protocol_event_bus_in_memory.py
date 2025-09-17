"""
Protocol for In-Memory Event Bus Implementation.

Defines the interface for in-memory event bus implementations.
"""

from typing import Protocol, runtime_checkable

from omnibase_core.protocol.protocol_event_bus_types import ProtocolEventBus


@runtime_checkable
class ProtocolEventBusInMemory(ProtocolEventBus, Protocol):
    """Protocol for in-memory event bus implementations."""

    def get_event_history(self) -> list:
        """Get the history of events processed by this in-memory event bus."""
        ...

    def clear_event_history(self) -> None:
        """Clear the event history."""
        ...

    def get_subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        ...
