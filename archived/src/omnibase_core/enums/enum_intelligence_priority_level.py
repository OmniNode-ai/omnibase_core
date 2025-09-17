"""
Enum for intelligence priority levels with validation.

Provides structured priority level definitions for intelligence
context sharing and processing prioritization.
"""

from enum import Enum


class EnumIntelligencePriorityLevel(str, Enum):
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
