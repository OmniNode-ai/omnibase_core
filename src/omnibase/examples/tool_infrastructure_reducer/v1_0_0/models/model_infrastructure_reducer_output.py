"""Output model for Infrastructure Reducer operations."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ModelInfrastructureReducerOutput(BaseModel):
    """Output model for Infrastructure Reducer operations."""

    status: str = Field(..., description="Status of the reduction operation")
    aggregated_result: Dict[str, Any] = Field(
        ..., description="Aggregated result from all adapter inputs"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if operation failed"
    )
