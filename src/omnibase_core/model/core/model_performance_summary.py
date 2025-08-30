"""
PerformanceSummary model.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ModelPerformanceSummary(BaseModel):
    """
    Performance summary with typed fields.
    Replaces Dict[str, Any] for get_performance_summary() returns.
    """

    total_execution_time_ms: float = Field(..., description="Total execution time")
    average_response_time_ms: Optional[float] = Field(
        None, description="Average response time"
    )
    min_response_time_ms: Optional[float] = Field(
        None, description="Minimum response time"
    )
    max_response_time_ms: Optional[float] = Field(
        None, description="Maximum response time"
    )
    p50_response_time_ms: Optional[float] = Field(
        None, description="50th percentile response time"
    )
    p95_response_time_ms: Optional[float] = Field(
        None, description="95th percentile response time"
    )
    p99_response_time_ms: Optional[float] = Field(
        None, description="99th percentile response time"
    )
    requests_per_second: Optional[float] = Field(
        None, description="Requests per second"
    )
    bytes_per_second: Optional[float] = Field(None, description="Bytes per second")
    total_requests: int = Field(0, description="Total number of requests")
    successful_requests: int = Field(0, description="Number of successful requests")
    failed_requests: int = Field(0, description="Number of failed requests")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    cache_hits: Optional[int] = Field(None, description="Number of cache hits")
    cache_misses: Optional[int] = Field(None, description="Number of cache misses")
    cache_hit_rate: Optional[float] = Field(
        None, description="Cache hit rate percentage"
    )
    error_rate: Optional[float] = Field(None, description="Error rate percentage")
    timeout_count: Optional[int] = Field(None, description="Number of timeouts")
    measurement_start: datetime = Field(..., description="Measurement start time")
    measurement_end: datetime = Field(..., description="Measurement end time")
    measurement_duration_seconds: float = Field(..., description="Measurement duration")
    model_config = ConfigDict()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    def calculate_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests * 100

    def calculate_average_response_time(self) -> Optional[float]:
        """Calculate average response time if not already set."""
        if self.average_response_time_ms is not None:
            return self.average_response_time_ms
        if self.total_requests > 0 and self.total_execution_time_ms > 0:
            return self.total_execution_time_ms / self.total_requests
        return None

    @field_serializer("measurement_start", "measurement_end")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
