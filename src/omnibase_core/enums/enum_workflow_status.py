"""
Workflow status enumeration.

Enumeration of possible workflow execution status values for ONEX workflows.
This is the canonical enum for workflow status - all workflow status tracking
should use this enum.

Consolidates: EnumWorkflowState, enum_workflow_coordination.EnumWorkflowStatus
"""

from enum import Enum, unique


@unique
class EnumWorkflowStatus(str, Enum):
    """
    Canonical workflow execution status enumeration.

    Used for tracking workflow state across the ONEX workflow coordination,
    execution, and monitoring subsystems.

    Values:
        PENDING: Workflow is queued but not yet started
        RUNNING: Workflow is actively executing
        COMPLETED: Workflow finished successfully
        FAILED: Workflow terminated due to an error
        CANCELLED: Workflow was manually or programmatically cancelled
        PAUSED: Workflow execution is temporarily suspended
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_terminal(cls, status: "EnumWorkflowStatus") -> bool:
        """Check if the status represents a terminal state."""
        return status in {cls.COMPLETED, cls.FAILED, cls.CANCELLED}

    @classmethod
    def is_active(cls, status: "EnumWorkflowStatus") -> bool:
        """Check if the status represents an active workflow."""
        return status in {cls.PENDING, cls.RUNNING, cls.PAUSED}

    @classmethod
    def is_successful(cls, status: "EnumWorkflowStatus") -> bool:
        """Check if the status represents successful completion."""
        return status == cls.COMPLETED

    @classmethod
    def is_error_state(cls, status: "EnumWorkflowStatus") -> bool:
        """Check if the status represents an error state."""
        return status == cls.FAILED


__all__ = ["EnumWorkflowStatus"]
