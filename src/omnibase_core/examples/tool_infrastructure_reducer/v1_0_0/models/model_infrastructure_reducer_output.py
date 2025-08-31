"""Output model for Infrastructure Reducer operations."""

from typing import Any

from pydantic import BaseModel, Field


class ModelInfrastructureReducerOutput(BaseModel):
    """Output model for Infrastructure Reducer operations."""

    status: str = Field(..., description="Status of the reduction operation")
    aggregated_result: dict[str, Any] = Field(
        ...,
        description="Aggregated result from all adapter inputs",
    )
    error_message: str | None = Field(
        None,
        description="Error message if operation failed",
    )
