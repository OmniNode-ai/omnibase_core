"""
Performance Metrics Model

Model for performance metrics of a node.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelPerformanceMetrics(BaseModel):
    """Performance metrics for the node"""

    uptime_seconds: Optional[float] = Field(
        None, description="Node uptime in seconds", ge=0.0
    )
    requests_per_minute: Optional[float] = Field(
        None, description="Average requests processed per minute", ge=0.0
    )
    average_response_time_ms: Optional[float] = Field(
        None, description="Average response time in milliseconds", ge=0.0
    )
    error_rate_percent: Optional[float] = Field(
        None, description="Error rate percentage (0.0-100.0)", ge=0.0, le=100.0
    )
    queue_depth: Optional[int] = Field(None, description="Current queue depth", ge=0)
