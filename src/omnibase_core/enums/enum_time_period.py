"""
Time period enumeration for trend data models.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTimePeriod(StrValueHelper, str, Enum):
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


# Export for use
__all__ = ["EnumTimePeriod"]
