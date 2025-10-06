"""Telemetry operation success metadata model."""

from pydantic import BaseModel, Field


class ModelTelemetryOperationSuccessMetadata(BaseModel):
    """Metadata for telemetry operation success events."""

    operation: str = Field(..., description="Name of the operation that succeeded")
    function: str = Field(..., description="Name of the function that was executed")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    result_type: str = Field(..., description="Type of the result returned")
    success: bool = Field(True, description="Whether the operation succeeded")
