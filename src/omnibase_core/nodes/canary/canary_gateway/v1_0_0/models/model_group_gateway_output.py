"""Output model for Group Gateway operations."""

from typing import Optional

from pydantic import BaseModel, Field

from .model_aggregated_response import ModelAggregatedResponse
from .model_routing_metrics import ModelRoutingMetrics


class ModelGroupGatewayOutput(BaseModel):
    """Output model for Group Gateway operations."""

    status: str = Field(..., description="Operation status")
    aggregated_response: ModelAggregatedResponse = Field(
        ..., description="Aggregated response data"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if operation failed"
    )
    cache_hit: Optional[bool] = Field(
        None, description="Whether response was served from cache"
    )
    routing_metrics: Optional[ModelRoutingMetrics] = Field(
        None, description="Routing performance metrics"
    )
