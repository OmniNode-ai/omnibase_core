"""Canonical workflow status enum for ONEX framework.

**BREAKING CHANGE** (OMN-1310): This enum consolidates multiple previous
workflow status enums into a single canonical source. No backwards
compatibility is provided.

**Consolidated enums**:
- EnumWorkflowState (deleted from enum_workflow_execution.py and enum_orchestrator_types.py)
- EnumWorkflowStatus (deleted from enum_workflow_coordination.py)

**Usage**: Import directly from omnibase_core.enums::

    from omnibase_core.enums import EnumWorkflowStatus

**Semantic Category**: Workflows (workflow lifecycle states)

**Migration**: Replace all imports of EnumWorkflowState or the old
EnumWorkflowStatus from enum_workflow_coordination.py with imports
from omnibase_core.enums.
"""

from enum import Enum, unique


@unique
class EnumWorkflowStatus(str, Enum):
    """Canonical workflow status enum for ONEX workflow lifecycle.

    This is the single source of truth for workflow status values across
    the ONEX framework. Use for tracking workflow state in coordination,
    execution, and monitoring subsystems.

    **Semantic Category**: Workflows (workflow lifecycle states)

    Values:
        PENDING: Workflow is queued but not yet started
        RUNNING: Workflow is actively executing
        COMPLETED: Workflow finished successfully
        FAILED: Workflow terminated due to an error
        CANCELLED: Workflow was manually or programmatically cancelled
        PAUSED: Workflow execution is temporarily suspended

    Helper Methods:
        - :meth:`is_terminal`: Check if workflow has finished
        - :meth:`is_active`: Check if workflow is in progress
        - :meth:`is_successful`: Check if workflow succeeded
        - :meth:`is_error_state`: Check if workflow failed

    .. versionchanged:: 0.6.4
        Consolidated EnumWorkflowState and enum_workflow_coordination.EnumWorkflowStatus
        into this enum (OMN-1310)
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
