"""
Kafka Publisher Metrics Models
Strongly-typed Pydantic models for Kafka publisher performance and metrics.
"""

from pydantic import BaseModel, Field


class ModelThroughputMetrics(BaseModel):
    """Kafka publisher throughput and performance metrics"""

    total_published: int = Field(..., description="Total number of events published")
    total_errors: int = Field(..., description="Total number of publishing errors")
    events_per_second: float = Field(..., description="Current events per second rate")
    error_rate: float = Field(..., description="Error rate percentage")
    circuit_breaker_failures: int = Field(
        ...,
        description="Number of circuit breaker failures",
    )
    circuit_breaker_open: bool = Field(
        ...,
        description="Whether circuit breaker is currently open",
    )
    last_publish_time: float | None = Field(
        None,
        description="Timestamp of last successful publish",
    )
