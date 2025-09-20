"""
Trend direction enumeration for directional trend analysis.

Provides strongly typed trend direction values for trend movement analysis.
Follows ONEX one-enum-per-file naming conventions.
"""

from enum import Enum


class EnumTrendDirection(str, Enum):
    """
    Strongly typed trend direction for directional trend analysis.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    UP = "up"
    DOWN = "down"
    FLAT = "flat"
    SIDEWAYS = "sideways"
    UPWARD_BREAKOUT = "upward_breakout"
    DOWNWARD_BREAKOUT = "downward_breakout"
    REVERSAL_UP = "reversal_up"
    REVERSAL_DOWN = "reversal_down"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_positive(cls, direction: "EnumTrendDirection") -> bool:
        """Check if the trend direction is positive."""
        return direction in {cls.UP, cls.UPWARD_BREAKOUT, cls.REVERSAL_UP}

    @classmethod
    def is_negative(cls, direction: "EnumTrendDirection") -> bool:
        """Check if the trend direction is negative."""
        return direction in {cls.DOWN, cls.DOWNWARD_BREAKOUT, cls.REVERSAL_DOWN}

    @classmethod
    def is_neutral(cls, direction: "EnumTrendDirection") -> bool:
        """Check if the trend direction is neutral."""
        return direction in {cls.FLAT, cls.SIDEWAYS}

    @classmethod
    def is_volatile(cls, direction: "EnumTrendDirection") -> bool:
        """Check if the trend direction is volatile."""
        return direction == cls.VOLATILE

    @classmethod
    def is_breakout(cls, direction: "EnumTrendDirection") -> bool:
        """Check if the trend direction is a breakout."""
        return direction in {cls.UPWARD_BREAKOUT, cls.DOWNWARD_BREAKOUT}

    @classmethod
    def is_reversal(cls, direction: "EnumTrendDirection") -> bool:
        """Check if the trend direction is a reversal."""
        return direction in {cls.REVERSAL_UP, cls.REVERSAL_DOWN}

    @classmethod
    def get_opposite(cls, direction: "EnumTrendDirection") -> "EnumTrendDirection":
        """Get the opposite trend direction."""
        opposite_map = {
            cls.UP: cls.DOWN,
            cls.DOWN: cls.UP,
            cls.UPWARD_BREAKOUT: cls.DOWNWARD_BREAKOUT,
            cls.DOWNWARD_BREAKOUT: cls.UPWARD_BREAKOUT,
            cls.REVERSAL_UP: cls.REVERSAL_DOWN,
            cls.REVERSAL_DOWN: cls.REVERSAL_UP,
            cls.FLAT: cls.FLAT,
            cls.SIDEWAYS: cls.SIDEWAYS,
            cls.VOLATILE: cls.VOLATILE,
            cls.UNKNOWN: cls.UNKNOWN,
        }
        return opposite_map.get(direction, cls.UNKNOWN)


# Export for use
__all__ = ["EnumTrendDirection"]