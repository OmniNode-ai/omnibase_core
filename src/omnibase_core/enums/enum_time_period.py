"""
Time period enumeration for trend data models.
"""

from __future__ import annotations

from enum import Enum


class EnumTimePeriod(str, Enum):
    """
    Enumeration for time periods in trend analysis.

    Provides type-safe options for time period classification.
    """

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    REAL_TIME = "real_time"
    CUSTOM = "custom"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


# Export for use
__all__ = ["EnumTimePeriod"]
