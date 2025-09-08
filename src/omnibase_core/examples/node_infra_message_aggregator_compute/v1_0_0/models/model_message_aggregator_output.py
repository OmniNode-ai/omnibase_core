"""Output model for Message Aggregator operations."""

from typing import Any

from pydantic import BaseModel, Field


class ModelMessageAggregatorOutput(BaseModel):
    """Output model for Message Aggregator operations."""

    status: str = Field(..., description="Status of the aggregation operation")
    aggregated_result: dict[str, Any] = Field(
        ...,
        description="Result of the message aggregation",
    )
    error_message: str | None = Field(
        None,
        description="Error message if operation failed",
    )
    state_snapshot: dict[str, Any] | None = Field(
        None,
        description="Current state snapshot after operation",
    )
    aggregation_metrics: dict[str, Any] | None = Field(
        None,
        description="Metrics about the aggregation operation",
    )
