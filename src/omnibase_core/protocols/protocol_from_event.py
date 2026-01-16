"""
Protocol for classes supporting construction from ModelOnexEvent.

This module provides a runtime-checkable protocol for type-safe checking of
the from_event class method pattern used by input state classes that can be
constructed from ONEX events.

Example:
    >>> from omnibase_core.protocols import ProtocolFromEvent
    >>>
    >>> class MyInputState:
    ...     @classmethod
    ...     def from_event(cls, event: ModelOnexEvent) -> "MyInputState":
    ...         return cls(...)
    >>>
    >>> isinstance(MyInputState, ProtocolFromEvent)  # True at runtime
"""

from typing import Any, Protocol, runtime_checkable

__all__ = ["ProtocolFromEvent"]


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
