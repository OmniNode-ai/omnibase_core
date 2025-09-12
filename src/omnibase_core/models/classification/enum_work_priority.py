"""
Enum for work priority levels.

Defines priority levels for work items.
"""

from enum import Enum


class EnumWorkPriority(str, Enum):
    """Priority levels for work items."""

    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    DEFERRED = "deferred"
