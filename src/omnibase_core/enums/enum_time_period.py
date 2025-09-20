"""
Time period enumeration for temporal operations.

Provides strongly typed time period values for time-based analysis and scheduling.
Follows ONEX one-enum-per-file naming conventions.
"""

from enum import Enum


class EnumTimePeriod(str, Enum):
    """
    Strongly typed time period for temporal operations.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    DECADE = "decade"
    REAL_TIME = "real_time"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_short_term(cls, period: "EnumTimePeriod") -> bool:
        """Check if the time period is short-term."""
        return period in {cls.SECOND, cls.MINUTE, cls.HOUR, cls.REAL_TIME}

    @classmethod
    def is_medium_term(cls, period: "EnumTimePeriod") -> bool:
        """Check if the time period is medium-term."""
        return period in {cls.DAY, cls.WEEK, cls.MONTH}

    @classmethod
    def is_long_term(cls, period: "EnumTimePeriod") -> bool:
        """Check if the time period is long-term."""
        return period in {cls.QUARTER, cls.YEAR, cls.DECADE}

    @classmethod
    def get_duration_seconds(cls, period: "EnumTimePeriod") -> int:
        """Get approximate duration in seconds."""
        duration_map = {
            cls.SECOND: 1,
            cls.MINUTE: 60,
            cls.HOUR: 3600,
            cls.DAY: 86400,
            cls.WEEK: 604800,
            cls.MONTH: 2592000,  # 30 days
            cls.QUARTER: 7776000,  # 90 days
            cls.YEAR: 31536000,  # 365 days
            cls.DECADE: 315360000,  # 10 years
            cls.REAL_TIME: 0,  # Immediate
        }
        return duration_map.get(period, 0)


# Export for use
__all__ = ["EnumTimePeriod"]