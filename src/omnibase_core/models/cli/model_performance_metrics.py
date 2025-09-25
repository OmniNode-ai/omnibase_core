"""
Performance Metrics Model.

Restrictive model for CLI execution performance metrics
with proper typing and validation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelPerformanceMetrics(BaseModel):
    """Restrictive model for performance metrics."""

    execution_time_ms: float = Field(description="Execution time in milliseconds")
    memory_usage_mb: float = Field(default=0.0, description="Memory usage in MB")
    cpu_usage_percent: float = Field(default=0.0, description="CPU usage percentage")
    io_operations: int = Field(default=0, description="Number of I/O operations")
    network_calls: int = Field(default=0, description="Number of network calls")
