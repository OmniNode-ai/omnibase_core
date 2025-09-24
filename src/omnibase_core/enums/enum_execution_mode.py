"""
Execution Mode Enum.

Strongly typed execution mode values for configuration.
"""

from __future__ import annotations

from enum import Enum


class EnumExecutionMode(str, Enum):
    """Strongly typed execution mode values."""

    AUTO = "AUTO"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    TRIGGER_BASED = "trigger_based"


# Export for use
__all__ = ["EnumExecutionMode"]
