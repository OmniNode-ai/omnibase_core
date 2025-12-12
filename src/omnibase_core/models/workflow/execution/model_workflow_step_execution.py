"""
Workflow Step Execution Model.

Runtime execution tracker for workflow steps with state management.
Different from ModelWorkflowStep (configuration) - this tracks execution state.

Extracted from node_orchestrator.py to eliminate embedded class anti-pattern.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_execution import (
    EnumBranchCondition,
    EnumExecutionMode,
    EnumWorkflowState,
)
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.utils.util_decorators import allow_dict_str_any

__all__ = ["ModelWorkflowStepExecution"]


@allow_dict_str_any(
    "Workflow step execution inputs and results fields require dict[str, Any] "
    "for flexible step-specific data across different step types."
)
class ModelWorkflowStepExecution(BaseModel):
    """
    Single step in a workflow with execution metadata and state tracking.

    This model tracks runtime execution state, distinct from ModelWorkflowStep
    which defines workflow step configuration.

    Runtime properties:
    - State tracking (PENDING -> RUNNING -> COMPLETED/FAILED)
    - Execution timestamps
    - Error tracking
    - Result collection
    """

    model_config = {
        "extra": "ignore",
        "arbitrary_types_allowed": True,  # For Callable[..., Any] and Exception
        "use_enum_values": False,
        "validate_assignment": True,
    }

    step_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this step",
    )

    step_name: str = Field(
        default=...,
        description="Human-readable name for this step",
        min_length=1,
        max_length=200,
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

    condition_function: Callable[..., Any] | None = Field(
        default=None,
        description="Custom condition function for branching",
        exclude=True,  # Not serializable
    )

    timeout_ms: int = Field(
        default=30000,
        description="Step execution timeout in milliseconds",
        ge=100,
        le=300000,  # Max 5 minutes
    )

    retry_count: int = Field(
        default=0,
        description="Number of retry attempts on failure",
        ge=0,
        le=10,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for step execution",
    )

    # Runtime state tracking
    state: EnumWorkflowState = Field(
        default=EnumWorkflowState.PENDING,
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

    results: list[Any] = Field(
        default_factory=list,
        description="Execution results from this step",
    )
