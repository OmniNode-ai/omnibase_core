"""
Time Unit Enumeration.

Time unit enumeration for flexible time representation.
"""

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
        names = {
            self.MILLISECONDS: "Milliseconds",
            self.SECONDS: "Seconds",
            self.MINUTES: "Minutes",
            self.HOURS: "Hours",
            self.DAYS: "Days",
        }
        return names[self]

    def to_milliseconds_multiplier(self) -> int:
        """Get multiplier to convert this unit to milliseconds."""
        multipliers = {
            self.MILLISECONDS: 1,
            self.SECONDS: 1000,
            self.MINUTES: 60 * 1000,
            self.HOURS: 60 * 60 * 1000,
            self.DAYS: 24 * 60 * 60 * 1000,
        }
        return multipliers[self]


# Export for use
__all__ = ["EnumTimeUnit"]
