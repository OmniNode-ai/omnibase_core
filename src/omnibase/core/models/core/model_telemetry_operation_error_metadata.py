"""Telemetry operation error metadata model."""

from pydantic import BaseModel, Field


class ModelTelemetryOperationErrorMetadata(BaseModel):
    """Metadata for telemetry operation error events."""

    operation: str = Field(..., description="Name of the operation that failed")
    function: str = Field(..., description="Name of the function that failed")
    execution_time_ms: float = Field(
        ..., description="Execution time in milliseconds before failure"
    )
    error_type: str = Field(..., description="Type of the error that occurred")
    error_message: str = Field(..., description="Error message")
    success: bool = Field(False, description="Whether the operation succeeded")
