"""Output model for Message Aggregator operations."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ModelMessageAggregatorOutput(BaseModel):
    """Output model for Message Aggregator operations."""

    status: str = Field(..., description="Status of the aggregation operation")
    aggregated_result: Dict[str, Any] = Field(
        ..., description="Result of the message aggregation"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if operation failed"
    )
    state_snapshot: Optional[Dict[str, Any]] = Field(
        None, description="Current state snapshot after operation"
    )
    aggregation_metrics: Optional[Dict[str, Any]] = Field(
        None, description="Metrics about the aggregation operation"
    )
