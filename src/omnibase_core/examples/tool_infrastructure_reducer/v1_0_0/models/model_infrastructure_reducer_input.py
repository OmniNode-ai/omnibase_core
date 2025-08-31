"""Input model for Infrastructure Reducer operations."""

from typing import Any

from pydantic import BaseModel, Field


class ModelInfrastructureReducerInput(BaseModel):
    """Input model for Infrastructure Reducer operations."""

    operation_type: str = Field(
        ...,
        description="Type of reduction operation to perform",
    )
    adapter_results: list[dict[str, Any]] = Field(
        ...,
        description="Results from infrastructure adapters to aggregate",
    )
    correlation_id: str | None = Field(
        None,
        description="Correlation ID for tracking the operation",
    )
