"""
Enum for checkpoint types.
Single responsibility: Centralized checkpoint type definitions.
"""

from enum import Enum


class EnumCheckpointType(str, Enum):
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
    COMPOSITION_BOUNDARY = "composition_boundary"  # At composition/decomposition boundaries

    def __str__(self) -> str:
        """Return the string value of the checkpoint type."""
        return self.value

    @classmethod
    def is_recovery_related(cls, checkpoint_type: "EnumCheckpointType") -> bool:
        """
        Check if the checkpoint type is related to recovery operations.

        Args:
            checkpoint_type: The checkpoint type to check

        Returns:
            True if recovery-related, False otherwise
        """
        recovery_types = {cls.FAILURE_RECOVERY, cls.RECOVERY, cls.SNAPSHOT}
        return checkpoint_type in recovery_types

    @classmethod
    def is_automatic(cls, checkpoint_type: "EnumCheckpointType") -> bool:
        """
        Check if the checkpoint type is automatically triggered.

        Args:
            checkpoint_type: The checkpoint type to check

        Returns:
            True if automatic, False if manual
        """
        return checkpoint_type != cls.MANUAL
