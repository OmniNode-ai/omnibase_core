"""Performance statistics model with strong typing."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelPerformanceStatistics(BaseModel):
    """Strongly typed performance statistics model."""

    total_requests: int = Field(ge=0, description="Total number of requests processed")
    successful_requests: int = Field(ge=0, description="Number of successful requests")
    failed_requests: int = Field(ge=0, description="Number of failed requests")

    average_response_time_ms: float = Field(
        ge=0.0, description="Average response time in milliseconds"
    )
    min_response_time_ms: float = Field(
        ge=0.0, description="Minimum response time in milliseconds"
    )
    max_response_time_ms: float = Field(
        ge=0.0, description="Maximum response time in milliseconds"
    )

    throughput_requests_per_second: float = Field(
        ge=0.0, description="Requests processed per second"
    )
    error_rate: float = Field(ge=0.0, le=1.0, description="Error rate as percentage")

    last_updated: datetime = Field(description="Timestamp of last statistics update")
    collection_period_seconds: int = Field(
        gt=0, description="Statistics collection period in seconds"
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelPerformanceMetadata(BaseModel):
    """Strongly typed performance metadata model."""

    operation_type: str = Field(
        min_length=1, description="Type of operation being monitored"
    )
    component_name: str = Field(
        min_length=1, description="Name of the component being monitored"
    )
    query_complexity: Optional[str] = Field(
        default=None, description="Complexity level of the query"
    )
    document_count: Optional[int] = Field(
        default=None, ge=0, description="Number of documents processed"
    )
    cache_hit: Optional[bool] = Field(
        default=None, description="Whether operation resulted in cache hit"
    )
    error_occurred: Optional[bool] = Field(
        default=None, description="Whether an error occurred during operation"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if error occurred"
    )

    model_config = ConfigDict(frozen=True, extra="forbid")
