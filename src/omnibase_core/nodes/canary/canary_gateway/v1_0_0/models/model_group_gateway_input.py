"""Input model for Group Gateway operations."""

from typing import List, Optional

from pydantic import BaseModel, Field

from .model_message_data import ModelMessageData


class ModelGroupGatewayInput(BaseModel):
    """Input model for Group Gateway operations."""

    operation_type: str = Field(
        ..., description="Type of operation: route, broadcast, aggregate"
    )
    target_tools: List[str] = Field(..., description="List of target tool endpoints")
    message_data: ModelMessageData = Field(..., description="Message data to route")
    correlation_id: Optional[str] = Field(
        None, description="Correlation ID for tracking"
    )
    timeout_ms: Optional[int] = Field(30000, description="Timeout in milliseconds")
    cache_strategy: Optional[str] = Field(
        "cache_aside", description="Caching strategy to use"
    )
