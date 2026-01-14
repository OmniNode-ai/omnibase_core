"""
Workflow Step Execution Model.

Runtime execution tracker for workflow steps with state management.
Different from ModelWorkflowStep (configuration) - this tracks execution state.

Extracted from node_orchestrator.py to eliminate embedded class anti-pattern.
"""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants import TIMEOUT_DEFAULT_MS, TIMEOUT_LONG_MS
from omnibase_core.constants.constants_field_limits import MAX_NAME_LENGTH
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.enums.enum_workflow_execution import (
    EnumBranchCondition,
    EnumExecutionMode,
)
from omnibase_core.models.orchestrator.model_action import ModelAction

__all__ = ["ModelWorkflowStepExecution"]


class ModelWorkflowStepExecution(BaseModel):
    """Single step in a workflow with execution metadata and state tracking.

    This model tracks runtime execution state, distinct from ModelWorkflowStep
    which defines workflow step configuration.

    Runtime properties:
        - State tracking (PENDING -> RUNNING -> COMPLETED/FAILED)
        - Execution timestamps
        - Error tracking
        - Result collection

    The from_attributes=True setting ensures proper instance recognition
    when nested in other Pydantic models or used with pytest-xdist.
    """

    model_config = ConfigDict(
        extra="ignore",
        arbitrary_types_allowed=True,  # For Callable[..., object] and Exception
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )

    step_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this step",
    )

    step_name: str = Field(
        default=...,
        description="Human-readable name for this step",
        min_length=1,
        max_length=MAX_NAME_LENGTH,
    )

    execution_mode: EnumExecutionMode = Field(
        default=...,
        description="Execution mode for this step",
    )

    thunks: list[ModelAction] = Field(
        default_factory=list,
        description="List of thunks to execute in this step",
    )

    condition: EnumBranchCondition | None = Field(
        default=None,
        description="Conditional branching type",
    )

    condition_function: Callable[..., object] | None = Field(
        default=None,
        description="Custom condition function for branching",
        exclude=True,  # Not serializable
    )

    timeout_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS,
        description="Step execution timeout in milliseconds",
        ge=100,
        le=TIMEOUT_LONG_MS,  # Max 5 minutes (TIMEOUT_LONG_MS)
    )

    retry_count: int = Field(
        default=0,
        description="Number of retry attempts on failure",
        ge=0,
        le=10,
    )

    # Runtime state tracking
    state: EnumExecutionStatus = Field(
        default=EnumExecutionStatus.PENDING,
        description="Current execution state",
    )

    started_at: datetime | None = Field(
        default=None,
        description="Timestamp when step execution started",
    )

    completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when step execution completed",
    )

    error: Exception | None = Field(
        default=None,
        description="Error if step execution failed",
        exclude=True,  # Not serializable
    )

    results: list[object] = Field(
        default_factory=list,
        description="Execution results from this step",
    )
