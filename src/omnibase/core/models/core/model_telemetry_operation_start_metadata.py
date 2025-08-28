"""Telemetry operation start metadata model."""

from typing import List

from pydantic import BaseModel, Field


class ModelTelemetryOperationStartMetadata(BaseModel):
    """Metadata for telemetry operation start events."""

    operation: str = Field(..., description="Name of the operation being started")
    function: str = Field(..., description="Name of the function being executed")
    args_count: int = Field(..., description="Number of arguments passed")
    kwargs_keys: List[str] = Field(..., description="Keys of keyword arguments")
