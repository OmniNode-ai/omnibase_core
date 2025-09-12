# Model for performance metrics
# DO NOT EDIT MANUALLY - regenerate using model generation tools


from pydantic import BaseModel, Field


class ModelPerformanceMetrics(BaseModel):
    """Model for performance metrics."""

    execution_time_ms: int = Field(
        default=0,
        description="Execution time in milliseconds",
    )
    memory_usage_mb: float = Field(default=0.0, description="Memory usage in megabytes")
    cpu_usage_percent: float = Field(default=0.0, description="CPU usage percentage")
    io_operations: int = Field(default=0, description="Number of I/O operations")
    network_calls: int = Field(default=0, description="Number of network calls")
    cache_hits: int = Field(default=0, description="Number of cache hits")
    cache_misses: int = Field(default=0, description="Number of cache misses")
