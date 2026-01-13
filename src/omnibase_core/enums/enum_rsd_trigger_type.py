"""
RSD Trigger Type Enumeration.

Defines trigger types for RSD (Rapid Service Development) algorithm.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRsdTriggerType(StrValueHelper, str, Enum):
    """Enumeration of RSD trigger types."""

    EVENT_DRIVEN = "event_driven"
    SCHEDULE_BASED = "schedule_based"
    MANUAL = "manual"
    THRESHOLD_BASED = "threshold_based"
    DEPENDENCY_BASED = "dependency_based"


__all__ = ["EnumRsdTriggerType"]
