"""
Time Unit Enumeration.

Time unit enumeration for flexible time representation.
"""

from __future__ import annotations

from enum import Enum


class EnumTimeUnit(Enum):
    """Time unit enumeration for flexible time representation."""

    MILLISECONDS = "ms"
    SECONDS = "s"
    MINUTES = "m"
    HOURS = "h"
    DAYS = "d"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        names: dict[EnumTimeUnit, str] = {
            EnumTimeUnit.MILLISECONDS: "Milliseconds",
            EnumTimeUnit.SECONDS: "Seconds",
            EnumTimeUnit.MINUTES: "Minutes",
            EnumTimeUnit.HOURS: "Hours",
            EnumTimeUnit.DAYS: "Days",
        }
        return names[self]

    def to_milliseconds_multiplier(self) -> int:
        """Get multiplier to convert this unit to milliseconds."""
        multipliers: dict[EnumTimeUnit, int] = {
            EnumTimeUnit.MILLISECONDS: 1,
            EnumTimeUnit.SECONDS: 1000,
            EnumTimeUnit.MINUTES: 60 * 1000,
            EnumTimeUnit.HOURS: 60 * 60 * 1000,
            EnumTimeUnit.DAYS: 24 * 60 * 60 * 1000,
        }
        return multipliers[self]


# Export for use
__all__ = ["EnumTimeUnit"]
