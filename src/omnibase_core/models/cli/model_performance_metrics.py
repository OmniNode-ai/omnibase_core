"""
Performance Metrics Model.

Restrictive model for CLI execution performance metrics
with proper typing and validation.
"""

from pydantic import BaseModel, Field


class ModelPerformanceMetrics(BaseModel):
    """Restrictive model for performance metrics."""

    execution_time_ms: float = Field(description="Execution time in milliseconds")
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")
    cpu_usage_percent: float | None = Field(None, description="CPU usage percentage")
    io_operations: int | None = Field(None, description="Number of I/O operations")
    network_calls: int | None = Field(None, description="Number of network calls")
