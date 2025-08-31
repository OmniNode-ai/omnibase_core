"""
Enum for execution modes.

Defines execution modes for work items.
"""

from enum import Enum


class EnumExecutionMode(str, Enum):
    """Execution modes for work items."""

    FULLY_AUTONOMOUS = "fully_autonomous"
    SEMI_AUTONOMOUS = "semi_autonomous"
    HUMAN_GUIDED = "human_guided"
    HUMAN_ONLY = "human_only"
