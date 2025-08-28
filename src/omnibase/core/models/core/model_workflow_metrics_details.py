"""
Model for workflow metrics details.

Structured model for workflow metrics details, replacing Dict[str, Any]
with proper typing for workflow metrics.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelWorkflowMetricsDetails(BaseModel):
    """
    Structured model for workflow metrics details.

    Replaces Dict[str, Any] with proper typing for workflow metrics.
    """

    throughput_per_second: Optional[float] = Field(
        None, description="Operations per second"
    )
    success_rate: Optional[float] = Field(None, description="Success rate percentage")
    average_latency_ms: Optional[float] = Field(
        None, description="Average latency in milliseconds"
    )
    peak_latency_ms: Optional[float] = Field(
        None, description="Peak latency in milliseconds"
    )
    queue_time_ms: Optional[float] = Field(
        None, description="Average queue time in milliseconds"
    )
    retry_count: Optional[int] = Field(None, description="Number of retries")
    timeout_count: Optional[int] = Field(None, description="Number of timeouts")
    data_processed_bytes: Optional[int] = Field(
        None, description="Total data processed in bytes"
    )
    parallel_executions: Optional[int] = Field(
        None, description="Number of parallel executions"
    )
    cache_hit_rate: Optional[float] = Field(
        None, description="Cache hit rate percentage"
    )
