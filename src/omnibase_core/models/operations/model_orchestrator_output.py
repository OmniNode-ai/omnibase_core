import uuid
from typing import List

from pydantic import Field

"""
Orchestrator Output Model - ONEX Standards Compliant.

Output model for NodeOrchestrator operations with workflow execution results.

Extracted from node_orchestrator.py to eliminate embedded class anti-pattern.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_execution import EnumWorkflowState
from omnibase_core.models.orchestrator.model_thunk import ModelThunk


class ModelOrchestratorOutput(BaseModel):
    """
    Output model for NodeOrchestrator operations.

    Strongly typed output wrapper with workflow execution
    results and coordination metadata.
    """

    workflow_id: UUID = Field(
        ...,
        description="Workflow identifier",
    )

    operation_id: UUID = Field(
        ...,
        description="Operation identifier",
    )

    workflow_state: EnumWorkflowState = Field(
        ...,
        description="Final workflow execution state",
    )

    steps_completed: int = Field(
        ...,
        description="Number of steps successfully completed",
        ge=0,
    )

    steps_failed: int = Field(
        ...,
        description="Number of steps that failed",
        ge=0,
    )

    thunks_emitted: list[ModelThunk] = Field(
        ...,
        description="List of thunks emitted during workflow execution",
    )

    processing_time_ms: float = Field(
        ...,
        description="Total processing time in milliseconds",
        ge=0,
    )

    parallel_executions: int = Field(
        default=0,
        description="Number of parallel execution waves",
        ge=0,
    )

    load_balanced_operations: int = Field(
        default=0,
        description="Number of operations that were load balanced",
        ge=0,
    )

    dependency_violations: int = Field(
        default=0,
        description="Number of dependency violations detected",
        ge=0,
    )

    results: list[Any] = Field(
        default_factory=list,
        description="Execution results from workflow steps",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from workflow execution",
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when workflow completed",
    )

    model_config = {
        "extra": "ignore",
        "arbitrary_types_allowed": True,
        "use_enum_values": False,
        "validate_assignment": True,
    }
