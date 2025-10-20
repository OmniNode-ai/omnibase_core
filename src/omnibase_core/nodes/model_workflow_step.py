"""
ModelWorkflowStep - Single step in a workflow with execution metadata.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.nodes.enum_orchestrator_types import (
    EnumBranchCondition,
    EnumExecutionMode,
    EnumWorkflowState,
)
from omnibase_core.nodes.model_action import ModelAction


class ModelWorkflowStep(BaseModel):
    """
    Single step in a workflow with execution metadata.

    Uses UUID for step_id to ensure strong typing and correlation tracking
    across distributed workflow execution.
    """

    step_id: UUID = Field(default_factory=uuid4, description="Unique step identifier")
    step_name: str = Field(..., description="Human-readable step name")
    execution_mode: EnumExecutionMode = Field(
        ..., description="Execution mode for step"
    )
    thunks: list[ModelAction] = Field(
        default_factory=list, description="List of thunks to execute"
    )
    condition: EnumBranchCondition | None = Field(
        None, description="Optional branching condition"
    )
    condition_function: Callable[..., Any] | None = Field(
        None, description="Optional custom condition function"
    )
    timeout_ms: int = Field(default=30000, description="Step timeout in milliseconds")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional step metadata"
    )
    state: EnumWorkflowState = Field(
        default=EnumWorkflowState.PENDING, description="Current step state"
    )
    started_at: datetime | None = Field(None, description="Step start timestamp")
    completed_at: datetime | None = Field(None, description="Step completion timestamp")
    error: Exception | None = Field(None, description="Error if step failed")
    results: list[Any] = Field(
        default_factory=list, description="Step execution results"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)
