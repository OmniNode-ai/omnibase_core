"""Subreducer result model for Reducer Pattern Engine."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .model_workflow_error import ModelWorkflowError
from .model_workflow_result import ModelWorkflowResult


class ModelSubreducerResult(BaseModel):
    """
    Result from subreducer processing.

    Contains the processing outcome from a specific subreducer
    including success/failure status and detailed results.
    """

    workflow_id: UUID = Field(..., description="Unique workflow identifier")
    subreducer_name: str = Field(
        ...,
        description="Name of the subreducer that processed the workflow",
    )
    success: bool = Field(..., description="Whether subreducer processing succeeded")
    result: ModelWorkflowResult = Field(..., description="Processing result details")
    error: ModelWorkflowError = Field(
        default_factory=ModelWorkflowError,
        description="Error details if processing failed",
    )
    processing_time_ms: float = Field(
        ...,
        description="Processing time in milliseconds",
    )
    processed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Processing completion timestamp",
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }
