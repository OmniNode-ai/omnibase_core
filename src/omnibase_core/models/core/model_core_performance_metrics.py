"""
Performance Metrics Model.

Structured performance metrics for action execution.
"""

from pydantic import BaseModel, Field


class ModelPerformanceMetrics(BaseModel):
    """Structured performance metrics for action execution."""

    execution_time_ms: int | None = Field(
        default=None,
        description="Total execution time in milliseconds",
    )
    memory_usage_mb: float | None = Field(
        default=None,
        description="Peak memory usage in MB",
    )
    cpu_usage_percent: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="CPU usage percentage",
    )
    io_operations: int | None = Field(
        default=None, description="Number of I/O operations"
    )
    network_requests: int | None = Field(
        default=None,
        description="Number of network requests",
    )
    cache_hits: int | None = Field(default=None, description="Number of cache hits")
    cache_misses: int | None = Field(default=None, description="Number of cache misses")

    def get_cache_hit_ratio(self) -> float | None:
        """Calculate cache hit ratio if cache metrics are available."""
        if self.cache_hits is not None and self.cache_misses is not None:
            total = self.cache_hits + self.cache_misses
            return self.cache_hits / total if total > 0 else 0.0
        return None
