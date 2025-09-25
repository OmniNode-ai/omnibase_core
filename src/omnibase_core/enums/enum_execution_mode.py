"""
Execution Mode Enum.

Strongly typed execution mode values for configuration.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumExecutionMode(str, Enum):
    """Strongly typed execution mode values."""

    AUTO = "auto"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    TRIGGER_BASED = "trigger_based"


# Export for use
__all__ = ["EnumExecutionMode"]
