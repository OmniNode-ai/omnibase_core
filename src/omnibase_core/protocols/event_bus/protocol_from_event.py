"""
ProtocolFromEvent - Protocol for classes that support construction from ModelOnexEvent.

This protocol enables type-safe checking of the from_event class method pattern used by
input state classes that can be constructed from events.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolFromEvent(Protocol):
    """Protocol for classes that support construction from ModelOnexEvent.

    This protocol enables type-safe checking of the from_event class method
    pattern used by input state classes that can be constructed from events.

    Example:
        >>> class MyInputState:
        ...     @classmethod
        ...     def from_event(cls, event: ModelOnexEvent) -> "MyInputState":
        ...         return cls(...)
        >>> isinstance(MyInputState, ProtocolFromEvent)  # True at runtime
    """

    @classmethod
    def from_event(cls, event: Any) -> Any:
        """Construct an instance from a ModelOnexEvent."""
        ...


__all__ = ["ProtocolFromEvent"]
