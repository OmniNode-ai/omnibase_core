"""
PerformanceSummary model.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ModelPerformanceSummary(BaseModel):
    """
    Performance summary with typed fields.

    Replaces Dict[str, Any] for get_performance_summary() returns.

    This model is frozen (immutable) and hashable, suitable for use as dict keys
    or in sets for caching and comparison purposes.

    Note on Methods:
        The `get_*` methods on this class are pure computed properties that derive
        values from existing fields without mutating state. This pattern is fully
        compatible with `frozen=True` - frozen models prevent field reassignment,
        but read-only methods that compute and return values are allowed.
    """

    total_execution_time_ms: float = Field(
        default=..., description="Total execution time"
    )
    average_response_time_ms: float | None = Field(
        default=None,
        description="Average response time",
    )
    min_response_time_ms: float | None = Field(
        default=None,
        description="Minimum response time",
    )
    max_response_time_ms: float | None = Field(
        default=None,
        description="Maximum response time",
    )
    p50_response_time_ms: float | None = Field(
        default=None,
        description="50th percentile response time",
    )
    p95_response_time_ms: float | None = Field(
        default=None,
        description="95th percentile response time",
    )
    p99_response_time_ms: float | None = Field(
        default=None,
        description="99th percentile response time",
    )
    requests_per_second: float | None = Field(
        default=None,
        description="Requests per second",
    )
    bytes_per_second: float | None = Field(default=None, description="Bytes per second")
    total_requests: int = Field(default=0, description="Total number of requests")
    successful_requests: int = Field(
        default=0, description="Number of successful requests"
    )
    failed_requests: int = Field(default=0, description="Number of failed requests")
    cpu_usage_percent: float | None = Field(
        default=None, description="CPU usage percentage"
    )
    memory_usage_mb: float | None = Field(
        default=None, description="Memory usage in MB"
    )
    cache_hits: int | None = Field(default=None, description="Number of cache hits")
    cache_misses: int | None = Field(default=None, description="Number of cache misses")
    cache_hit_rate: float | None = Field(
        default=None,
        description="Cache hit rate percentage",
    )
    error_rate: float | None = Field(default=None, description="Error rate percentage")
    timeout_count: int | None = Field(default=None, description="Number of timeouts")
    measurement_start: datetime = Field(
        default=..., description="Measurement start time"
    )
    measurement_end: datetime = Field(default=..., description="Measurement end time")
    measurement_duration_seconds: float = Field(
        default=..., description="Measurement duration"
    )
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    def get_success_rate(self) -> float:
        """
        Get success rate percentage.

        Pure computed property - derives value from existing fields without mutation.
        Compatible with frozen=True.

        Returns:
            Success rate as a percentage (0.0-100.0).
        """
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests * 100

    def get_average_response_time(self) -> float | None:
        """
        Get average response time, computing from totals if not explicitly set.

        Pure computed property - derives value from existing fields without mutation.
        Compatible with frozen=True.

        Returns:
            Average response time in milliseconds, or None if not calculable.
        """
        if self.average_response_time_ms is not None:
            return self.average_response_time_ms
        if self.total_requests > 0 and self.total_execution_time_ms > 0:
            return self.total_execution_time_ms / self.total_requests
        return None

    @field_serializer("measurement_start", "measurement_end")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None
