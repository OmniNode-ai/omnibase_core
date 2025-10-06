"""Telemetry operation error metadata model."""

from pydantic import BaseModel, Field


class ModelTelemetryOperationErrorMetadata(BaseModel):
    """Metadata for telemetry operation error events."""

    operation: str = Field(default=..., description="Name of the operation that failed")
    function: str = Field(default=..., description="Name of the function that failed")
    execution_time_ms: float = Field(
        default=...,
        description="Execution time in milliseconds before failure",
    )
    error_type: str = Field(default=..., description="Type of the error that occurred")
    error_message: str = Field(default=..., description="Error message")
    success: bool = Field(default=False, description="Whether the operation succeeded")
