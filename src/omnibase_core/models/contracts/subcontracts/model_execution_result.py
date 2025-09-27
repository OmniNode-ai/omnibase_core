"""
Execution Result Model - ONEX Standards Compliant.

Model for workflow execution results in the ONEX workflow coordination system.
"""

from typing import Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_coordination import EnumWorkflowStatus

from .model_workflow_metrics import ModelWorkflowMetrics

# Type aliases for structured data - ZERO TOLERANCE for Any types
ParameterValue = Union[str, int, float, bool, None]
StructuredData = dict[str, ParameterValue]


class ModelExecutionResult(BaseModel):
    """Result of workflow execution."""

    workflow_id: UUID = Field(default_factory=uuid4, description="Workflow identifier")

    status: EnumWorkflowStatus = Field(..., description="Final status of the workflow")

    execution_time_ms: int = Field(
        ..., description="Total execution time in milliseconds", ge=0
    )

    result_data: StructuredData = Field(
        default_factory=dict, description="Result data from the workflow"
    )

    error_message: Optional[str] = Field(
        default=None, description="Error message if workflow failed"
    )

    coordination_metrics: ModelWorkflowMetrics = Field(
        ..., description="Performance metrics for the execution"
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
