"""
ModelOrchestratorOutput - Output model for NodeOrchestrator operations.

Strongly typed output wrapper with workflow execution
results and coordination metadata.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_orchestrator_types import EnumWorkflowState
from omnibase_core.models.orchestrator.model_action import ModelAction


class ModelOrchestratorOutput(BaseModel):
    """
    Output model for NodeOrchestrator operations.

    Strongly typed output wrapper with workflow execution
    results and coordination metadata.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    workflow_id: UUID = Field(..., description="Workflow identifier")
    operation_id: UUID = Field(..., description="Operation identifier")
    workflow_state: EnumWorkflowState = Field(..., description="Final workflow state")
    steps_completed: int = Field(
        ..., description="Number of successfully completed steps"
    )
    steps_failed: int = Field(..., description="Number of failed steps")
    actions_emitted: list[ModelAction] = Field(
        default_factory=list, description="List of emitted actions"
    )
    processing_time_ms: float = Field(
        ..., description="Total processing time in milliseconds"
    )
    parallel_executions: int = Field(
        default=0, description="Number of parallel execution batches"
    )
    load_balanced_operations: int = Field(
        default=0, description="Number of load-balanced operations"
    )
    dependency_violations: int = Field(
        default=0, description="Number of dependency violations detected"
    )
    results: list[Any] = Field(
        default_factory=list, description="Workflow execution results"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional workflow metadata"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Workflow completion timestamp"
    )
