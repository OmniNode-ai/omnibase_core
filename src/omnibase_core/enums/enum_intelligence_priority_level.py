"""
Enum for intelligence priority levels with validation.

Provides structured priority level definitions for intelligence
context sharing and processing prioritization.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumIntelligencePriorityLevel(StrValueHelper, str, Enum):
    """
    Enum for intelligence priority levels with validation.

    Defines priority levels for intelligence context processing
    and cross-instance sharing with proper validation.
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


__all__ = ["EnumIntelligencePriorityLevel"]
