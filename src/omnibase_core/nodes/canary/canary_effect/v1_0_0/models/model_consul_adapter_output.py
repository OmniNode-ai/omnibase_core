"""Output model for Consul Adapter operations."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ModelConsulAdapterOutput(BaseModel):
    """Output model for Consul Adapter operations."""

    operation_result: Optional[Dict[str, Any]] = Field(
        None, description="Result of the consul operation"
    )
    kv_data: Optional[Dict[str, Any]] = Field(
        None, description="Retrieved key-value data"
    )
    service_id: Optional[str] = Field(None, description="Registered service ID")
    success: bool = Field(..., description="Whether operation succeeded")
    error_message: Optional[str] = Field(
        None, description="Error message if operation failed"
    )
