"""
ModelValidatable Protocol.

Protocol for values that can validate themselves. Provides self-validation
interface for objects with built-in validation logic.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolModelValidatable(Protocol):
    """
    Protocol for values that can validate themselves.

    Provides self-validation interface for objects with built-in
    validation logic.
    """

    def is_valid(self) -> bool:
        """Check if the value is valid."""
        ...

    async def get_errors(self) -> list[str]:
        """Get validation errors."""
        ...


__all__ = ["ProtocolModelValidatable"]
