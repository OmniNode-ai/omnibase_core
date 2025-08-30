"""Input model for Message Aggregator operations."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelMessageAggregatorInput(BaseModel):
    """Input model for Message Aggregator operations."""

    operation_type: str = Field(
        ..., description="Type of aggregation operation to perform"
    )
    group_messages: List[Dict[str, Any]] = Field(
        ..., description="Messages from tool groups to aggregate"
    )
    aggregation_strategy: str = Field(
        ..., description="Strategy to use for message aggregation"
    )
    correlation_id: Optional[str] = Field(
        None, description="Correlation ID for tracking the operation"
    )
    timeout_ms: Optional[int] = Field(
        None, description="Timeout for aggregation operation in milliseconds"
    )
    state_key: Optional[str] = Field(
        None, description="Key for state management operations"
    )
