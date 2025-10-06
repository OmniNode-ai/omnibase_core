"""Telemetry operation success metadata model."""

from pydantic import BaseModel, Field


class ModelTelemetryOperationSuccessMetadata(BaseModel):
    """Metadata for telemetry operation success events."""

    operation: str = Field(
        default=..., description="Name of the operation that succeeded"
    )
    function: str = Field(
        default=..., description="Name of the function that was executed"
    )
    execution_time_ms: float = Field(
        default=..., description="Execution time in milliseconds"
    )
    result_type: str = Field(default=..., description="Type of the result returned")
    success: bool = Field(default=True, description="Whether the operation succeeded")
