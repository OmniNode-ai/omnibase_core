"""Telemetry operation start metadata model."""

from pydantic import BaseModel, Field


class ModelTelemetryOperationStartMetadata(BaseModel):
    """Metadata for telemetry operation start events."""

    operation: str = Field(
        default=..., description="Name of the operation being started"
    )
    function: str = Field(
        default=..., description="Name of the function being executed"
    )
    args_count: int = Field(default=..., description="Number of arguments passed")
    kwargs_keys: list[str] = Field(default=..., description="Keys of keyword arguments")
