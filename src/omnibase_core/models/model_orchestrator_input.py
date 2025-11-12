"""
ModelOrchestratorInput - Input model for NodeOrchestrator operations.

Strongly typed input wrapper for workflow coordination
with execution mode and branching configuration.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode


class ModelOrchestratorInput(BaseModel):
    """
    Input model for NodeOrchestrator operations.

    Strongly typed input wrapper for workflow coordination
    with execution mode and branching configuration.
    """

    workflow_id: UUID = Field(..., description="Unique workflow identifier")
    steps: list[dict[str, Any]] = Field(
        ..., description="Simplified WorkflowStep representation"
    )
    operation_id: UUID = Field(
        default_factory=uuid4, description="Unique operation identifier"
    )
    execution_mode: EnumExecutionMode = Field(
        default=EnumExecutionMode.SEQUENTIAL, description="Execution mode for workflow"
    )
    max_parallel_steps: int = Field(
        default=5, description="Maximum number of parallel steps"
    )
    global_timeout_ms: int = Field(
        default=300000, description="Global workflow timeout (5 minutes default)"
    )
    failure_strategy: str = Field(
        default="fail_fast", description="Strategy for handling failures"
    )
    load_balancing_enabled: bool = Field(
        default=False, description="Enable load balancing for operations"
    )
    dependency_resolution_enabled: bool = Field(
        default=True, description="Enable automatic dependency resolution"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional workflow metadata"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Workflow creation timestamp"
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=False,
    )
