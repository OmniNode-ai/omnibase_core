"""
Simple Workflow Execution Result Model - ONEX Standards Compliant.

Domain-specific result model for workflow execution in the ONEX coordination system.
Replaces the generic ModelExecutionResult with a focused workflow-specific model.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import PrimitiveValueType
from omnibase_core.enums.enum_workflow_coordination import EnumWorkflowStatus
from omnibase_core.models.contracts.subcontracts.model_workflow_metrics import (
    ModelWorkflowMetrics,
)

# Type aliases for structured data
StructuredData = dict[str, PrimitiveValueType]


class ModelWorkflowExecutionResult(BaseModel):
    """
    Simple workflow execution result for ONEX coordination.

    Provides workflow-specific execution results with coordination metrics
    and performance tracking.

    ZERO TOLERANCE: No Any types allowed.
    """

    workflow_id: UUID = Field(default_factory=uuid4, description="Workflow identifier")

    status: EnumWorkflowStatus = Field(..., description="Final status of the workflow")

    execution_time_ms: int = Field(
        ...,
        description="Total execution time in milliseconds",
        ge=0,
    )

    result_data: StructuredData = Field(
        default_factory=dict,
        description="Result data from the workflow",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if workflow failed",
    )

    coordination_metrics: ModelWorkflowMetrics = Field(
        ...,
        description="Performance metrics for the execution",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


__all__ = ["ModelWorkflowExecutionResult"]
