"""
Scenario Status Enum.

Strongly typed status values for scenario execution.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumScenarioStatus(StrValueHelper, str, Enum):
    """Strongly typed scenario status values."""

    NOT_EXECUTED = "not_executed"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# Export for use
__all__ = ["EnumScenarioStatus"]
