"""
Tool performance metrics model.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelToolPerformanceMetrics(BaseModel):
    """Performance metrics for tool execution."""

    avg_execution_time_ms: float = Field(
        default=0.0,
        description="Average execution time in milliseconds",
    )
    success_rate_percent: float = Field(
        default=100.0, description="Success rate percentage"
    )
    error_rate_percent: float = Field(default=0.0, description="Error rate percentage")
    total_executions: int = Field(default=0, description="Total number of executions")
    last_execution_time: datetime | None = Field(
        default=None,
        description="Last execution timestamp",
    )
    memory_usage_mb: float = Field(
        default=0.0, description="Average memory usage in MB"
    )
    cpu_usage_percent: float = Field(
        default=0.0, description="Average CPU usage percentage"
    )
