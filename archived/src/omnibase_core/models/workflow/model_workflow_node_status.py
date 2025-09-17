"""Workflow node status model for tracking individual node execution state."""

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.models.execution.model_execution_result import ModelExecutionResult


class ModelWorkflowNodeStatus(BaseModel):
    """Workflow node execution status with detailed tracking."""

    status: EnumExecutionStatus = Field(..., description="Current execution status")
    start_time: float | None = Field(
        None,
        description="Execution start timestamp",
        gt=0,
    )
    end_time: float | None = Field(None, description="Execution end timestamp", gt=0)
    output: ModelExecutionResult | None = Field(
        None,
        description="Node execution output",
    )
    error_message: str | None = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retries attempted", ge=0)

    @field_validator("end_time")
    @classmethod
    def validate_end_time_after_start(cls, v, info):
        """Ensure end_time is after start_time."""
        if (
            v is not None
            and hasattr(info, "data")
            and "start_time" in info.data
            and info.data["start_time"] is not None
        ) and v <= info.data["start_time"]:
            msg = "end_time must be after start_time"
            raise ValueError(msg)
        return v
