"""
Execution Mode Enum.

Strongly typed execution mode values for configuration.
"""

from __future__ import annotations

from enum import Enum


class EnumExecutionMode(str, Enum):
    """Strongly typed execution mode values."""

    AUTO = "AUTO"
    MANUAL = "MANUAL"
    SCHEDULED = "SCHEDULED"
    TRIGGER_BASED = "TRIGGER_BASED"


# Export for use
__all__ = ["EnumExecutionMode"]
