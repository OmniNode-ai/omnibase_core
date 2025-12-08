"""
ProtocolSchemaValue - Protocol for schema values.

This module provides the protocol definition for schema value types.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolSchemaValue(Protocol):
    """
    Protocol for schema value types.

    Allows working with schema values without depending on
    the concrete ModelSchemaValue class.
    """

    def to_value(self) -> object:
        """Convert to Python value."""
        ...

    @classmethod
    def from_value(cls, value: object) -> ProtocolSchemaValue:
        """Create from Python value."""
        ...


__all__ = ["ProtocolSchemaValue"]
