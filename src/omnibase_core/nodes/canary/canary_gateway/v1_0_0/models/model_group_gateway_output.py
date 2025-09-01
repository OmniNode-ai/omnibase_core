"""Output model for Group Gateway operations."""

from pydantic import BaseModel, Field

from .model_aggregated_response import ModelAggregatedResponse
from .model_routing_metrics import ModelRoutingMetrics


class ModelGroupGatewayOutput(BaseModel):
    """Output model for Group Gateway operations."""

    status: str = Field(..., description="Operation status")
    aggregated_response: ModelAggregatedResponse = Field(
        ...,
        description="Aggregated response data",
    )
    error_message: str | None = Field(
        None,
        description="Error message if operation failed",
    )
    cache_hit: bool | None = Field(
        None,
        description="Whether response was served from cache",
    )
    routing_metrics: ModelRoutingMetrics | None = Field(
        None,
        description="Routing performance metrics",
    )
