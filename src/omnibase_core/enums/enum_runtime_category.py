"""
Runtime Category Enumeration.

Defines categories for estimated runtime durations.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRuntimeCategory(StrValueHelper, str, Enum):
    """
    Runtime category enumeration.

    Represents different categories of expected runtime durations.
    """

    # Ultra-fast operations (sub-second)
    INSTANT = "instant"  # < 100ms
    VERY_FAST = "very_fast"  # 100ms - 1s

    # Fast operations
    FAST = "fast"  # 1-5 seconds
    QUICK = "quick"  # 5-15 seconds

    # Moderate operations
    MODERATE = "moderate"  # 15 seconds - 1 minute
    STANDARD = "standard"  # 1-5 minutes

    # Longer operations
    LONG = "long"  # 5-15 minutes
    EXTENDED = "extended"  # 15-30 minutes

    # Very long operations
    VERY_LONG = "very_long"  # 30 minutes - 1 hour
    BATCH = "batch"  # 1-3 hours

    # Extreme durations
    MARATHON = "marathon"  # 3+ hours
    OVERNIGHT = "overnight"  # 8+ hours
    UNKNOWN = "unknown"  # Cannot estimate

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        return self.value.replace("_", " ").title()

    @property
    def estimated_seconds(self) -> tuple[float, float | None]:
        """Get estimated duration range in seconds."""
        ranges: dict[EnumRuntimeCategory, tuple[float, float | None]] = {
            EnumRuntimeCategory.INSTANT: (0, 0.1),
            EnumRuntimeCategory.VERY_FAST: (0.1, 1),
            EnumRuntimeCategory.FAST: (1, 5),
            EnumRuntimeCategory.QUICK: (5, 15),
            EnumRuntimeCategory.MODERATE: (15, 60),
            EnumRuntimeCategory.STANDARD: (60, 300),
            EnumRuntimeCategory.LONG: (300, 900),
            EnumRuntimeCategory.EXTENDED: (900, 1800),
            EnumRuntimeCategory.VERY_LONG: (1800, 3600),
            EnumRuntimeCategory.BATCH: (3600, 10800),
            EnumRuntimeCategory.MARATHON: (10800, None),
            EnumRuntimeCategory.OVERNIGHT: (28800, None),
            EnumRuntimeCategory.UNKNOWN: (0, None),
        }
        return ranges.get(self, (0, None))

    @property
    def estimated_minutes(self) -> tuple[float, float | None]:
        """Get estimated duration range in minutes."""
        seconds_range = self.estimated_seconds
        min_mins = seconds_range[0] / 60
        max_mins = seconds_range[1] / 60 if seconds_range[1] is not None else None
        return (min_mins, max_mins)

    @classmethod
    def from_seconds(cls, seconds: float) -> EnumRuntimeCategory:
        """Determine category from duration in seconds."""
        # Runtime threshold classification - architectural design for runtime categories
        if seconds < 0.1:
            return cls.INSTANT
        if seconds < 1:
            return cls.VERY_FAST
        if seconds < 5:
            return cls.FAST
        if seconds < 15:
            return cls.QUICK
        if seconds < 60:
            return cls.MODERATE
        if seconds < 300:
            return cls.STANDARD
        if seconds < 900:
            return cls.LONG
        if seconds < 1800:
            return cls.EXTENDED
        if seconds < 3600:
            return cls.VERY_LONG
        if seconds < 10800:
            return cls.BATCH
        if seconds < 28800:
            return cls.MARATHON
        return cls.OVERNIGHT

    @classmethod
    def get_fast_categories(cls) -> list[EnumRuntimeCategory]:
        """Get categories for fast operations."""
        return [
            cls.INSTANT,
            cls.VERY_FAST,
            cls.FAST,
            cls.QUICK,
        ]

    @classmethod
    def get_slow_categories(cls) -> list[EnumRuntimeCategory]:
        """Get categories for slow operations."""
        return [
            cls.MARATHON,
            cls.OVERNIGHT,
        ]


# Export for use
__all__ = ["EnumRuntimeCategory"]
