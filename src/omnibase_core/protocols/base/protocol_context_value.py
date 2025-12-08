"""
Context Value Protocol.

Core-native equivalent of SPI ContextValue. Context values are type-safe
containers for data passed between nodes and services in the ONEX architecture.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolContextValue(Protocol):
    """
    Protocol for context data values supporting validation and serialization.

    Context values are type-safe containers for data passed between nodes
    and services in the ONEX architecture.
    """

    async def validate_for_context(self) -> bool:
        """Validate the value for context usage."""
        ...

    def serialize_for_context(self) -> dict[str, object]:
        """Serialize the value for context transmission."""
        ...

    async def get_context_type_hint(self) -> str:
        """Get the type hint for this context value."""
        ...


# Type alias for simpler usage
ContextValue = ProtocolContextValue


__all__ = ["ProtocolContextValue", "ContextValue"]
