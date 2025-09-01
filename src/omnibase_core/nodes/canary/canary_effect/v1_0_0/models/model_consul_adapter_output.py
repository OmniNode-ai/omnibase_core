"""Output model for Consul Adapter operations."""

from typing import Any

from pydantic import BaseModel, Field


class ModelConsulAdapterOutput(BaseModel):
    """Output model for Consul Adapter operations."""

    operation_result: dict[str, Any] | None = Field(
        None,
        description="Result of the consul operation",
    )
    kv_data: dict[str, Any] | None = Field(
        None,
        description="Retrieved key-value data",
    )
    service_id: str | None = Field(None, description="Registered service ID")
    success: bool = Field(..., description="Whether operation succeeded")
    error_message: str | None = Field(
        None,
        description="Error message if operation failed",
    )
