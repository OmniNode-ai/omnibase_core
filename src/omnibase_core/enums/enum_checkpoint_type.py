"""
Enum for checkpoint types.
Single responsibility: Centralized checkpoint type definitions.
"""

from enum import Enum, unique
from functools import cache

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCheckpointType(StrValueHelper, str, Enum):
    """Types of workflow checkpoints for state persistence and recovery."""

    # Trigger-based checkpoints
    MANUAL = "manual"  # Explicitly triggered by user or operator
    AUTOMATIC = "automatic"  # Triggered by system rules or policies

    # Recovery checkpoints
    FAILURE_RECOVERY = "failure_recovery"  # Created for failure recovery purposes
    RECOVERY = "recovery"  # Generic recovery checkpoint

    # Progress checkpoints
    STEP_COMPLETION = "step_completion"  # Created after a workflow step completes
    STAGE_COMPLETION = "stage_completion"  # Created after a workflow stage completes

    # State capture checkpoints
    SNAPSHOT = "snapshot"  # Full state snapshot at a point in time
    INCREMENTAL = "incremental"  # Incremental state changes since last checkpoint

    # Boundary checkpoints
    COMPOSITION_BOUNDARY = (
        "composition_boundary"  # At composition/decomposition boundaries
    )

    @classmethod
    @cache
    def _recovery_types(cls) -> frozenset["EnumCheckpointType"]:
        """Return cached frozenset of recovery-related checkpoint types.

        Uses functools.cache for memoization to avoid recreating the frozenset on each call.
        """
        return frozenset({cls.FAILURE_RECOVERY, cls.RECOVERY, cls.SNAPSHOT})

    @classmethod
    @cache
    def _automatic_types(cls) -> frozenset["EnumCheckpointType"]:
        """Return cached frozenset of automatic checkpoint types.

        Uses functools.cache for memoization to avoid recreating the frozenset on each call.
        """
        return frozenset(
            {
                cls.AUTOMATIC,
                cls.FAILURE_RECOVERY,
                cls.RECOVERY,
                cls.STEP_COMPLETION,
                cls.STAGE_COMPLETION,
                cls.SNAPSHOT,
                cls.INCREMENTAL,
                cls.COMPOSITION_BOUNDARY,
            }
        )

    @classmethod
    def is_recovery_related(cls, checkpoint_type: "EnumCheckpointType") -> bool:
        """
        Check if the checkpoint type is related to recovery operations.

        Args:
            checkpoint_type: The checkpoint type to check

        Returns:
            True if recovery-related, False otherwise
        """
        return checkpoint_type in cls._recovery_types()

    @classmethod
    def is_automatic(cls, checkpoint_type: "EnumCheckpointType") -> bool:
        """
        Check if the checkpoint type is automatically triggered.

        Args:
            checkpoint_type: The checkpoint type to check

        Returns:
            True if automatic, False if manual
        """
        return checkpoint_type in cls._automatic_types()
