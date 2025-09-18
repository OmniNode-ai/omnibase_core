"""
Node performance metrics model.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelNodePerformanceMetrics(BaseModel):
    """Performance metrics for node execution."""

    avg_execution_time_ms: float = Field(
        0.0,
        description="Average execution time in milliseconds",
    )
    success_rate_percent: float = Field(100.0, description="Success rate percentage")
    error_rate_percent: float = Field(0.0, description="Error rate percentage")
    total_executions: int = Field(0, description="Total number of executions")
    last_execution_time: datetime | None = Field(
        None,
        description="Last execution timestamp",
    )
    memory_usage_mb: float = Field(0.0, description="Average memory usage in MB")
    cpu_usage_percent: float = Field(0.0, description="Average CPU usage percentage")
