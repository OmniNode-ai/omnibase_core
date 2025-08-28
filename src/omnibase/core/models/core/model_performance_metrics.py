"""
Performance Metrics Model.

Structured performance metrics for action execution.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelPerformanceMetrics(BaseModel):
    """Structured performance metrics for action execution."""

    execution_time_ms: Optional[int] = Field(
        None, description="Total execution time in milliseconds"
    )
    memory_usage_mb: Optional[float] = Field(
        None, description="Peak memory usage in MB"
    )
    cpu_usage_percent: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="CPU usage percentage"
    )
    io_operations: Optional[int] = Field(None, description="Number of I/O operations")
    network_requests: Optional[int] = Field(
        None, description="Number of network requests"
    )
    cache_hits: Optional[int] = Field(None, description="Number of cache hits")
    cache_misses: Optional[int] = Field(None, description="Number of cache misses")

    def get_cache_hit_ratio(self) -> Optional[float]:
        """Calculate cache hit ratio if cache metrics are available."""
        if self.cache_hits is not None and self.cache_misses is not None:
            total = self.cache_hits + self.cache_misses
            return self.cache_hits / total if total > 0 else 0.0
        return None
