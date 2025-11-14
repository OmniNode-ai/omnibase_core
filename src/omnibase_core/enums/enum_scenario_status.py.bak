from __future__ import annotations

"""
Scenario Status Enum.

Strongly typed status values for scenario execution.
"""


from enum import Enum, unique


@unique
class EnumScenarioStatus(str, Enum):
    """Strongly typed scenario status values."""

    NOT_EXECUTED = "not_executed"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# Export for use
__all__ = ["EnumScenarioStatus"]
