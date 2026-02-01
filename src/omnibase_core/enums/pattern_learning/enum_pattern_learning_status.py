"""Enumeration for pattern learning execution status.

Defines the execution states for pattern learning pipeline runs.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumPatternLearningStatus"]


@unique
class EnumPatternLearningStatus(StrValueHelper, str, Enum):
    """Execution status for pattern learning operations.

    Tracks the completion state of pattern learning pipeline runs.

    Example:
        .. code-block:: python

            from omnibase_core.enums.pattern_learning import EnumPatternLearningStatus

            status = EnumPatternLearningStatus.COMPLETED
            if status == EnumPatternLearningStatus.COMPLETED:
                process_results()

    .. versionadded:: 0.9.8
    """

    COMPLETED = "completed"
    """Learning run completed successfully."""

    FAILED = "failed"
    """Learning run failed with errors."""

    IN_PROGRESS = "in_progress"
    """Learning run is currently executing."""

    CANCELLED = "cancelled"
    """Learning run was cancelled before completion."""
