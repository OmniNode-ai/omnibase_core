"""
Status Protocol for enum migration operations.

This module defines the protocol that all status enums must implement
to be compatible with the migration system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from omnibase_core.enums.enum_base_status import EnumBaseStatus


class EnumStatusProtocol(Protocol):
    """Protocol for status enums that can be migrated and converted to base status."""

    value: str

    def to_base_status(self) -> EnumBaseStatus:
        """Convert this status to its base status equivalent."""
        ...


# TypeVar for type-safe enum migration (ONEX compliant)
StatusEnumType = type("StatusEnumType", (), {})  # Simple type variable

# Export for use
__all__ = [
    "EnumStatusProtocol",
]
