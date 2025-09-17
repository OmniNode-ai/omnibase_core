"""Model for routing performance metrics."""

from pydantic import BaseModel, Field


class ModelRoutingMetrics(BaseModel):
    """Model for routing performance metrics."""

    total_requests: int = Field(..., description="Total number of routing requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    average_response_time_ms: float = Field(..., description="Average response time")
    cache_hit_ratio: float = Field(..., description="Cache hit ratio")
