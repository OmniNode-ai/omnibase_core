from pydantic import Field

from omnibase_core.models.core.model_workflow import ModelWorkflow

"""
Model for workflow metrics details.

Structured model for workflow metrics details, replacing Dict[str, Any]
with proper typing for workflow metrics.
"""

from typing import Any

from pydantic import BaseModel


class ModelWorkflowMetricsDetails(BaseModel):
    """
    Structured model for workflow metrics details.

    Replaces Dict[str, Any] with proper typing for workflow metrics.
    """

    throughput_per_second: float | None = Field(
        default=None,
        description="Operations per second",
    )
    success_rate: float | None = Field(
        default=None, description="Success rate percentage"
    )
    average_latency_ms: float | None = Field(
        default=None,
        description="Average latency in milliseconds",
    )
    peak_latency_ms: float | None = Field(
        default=None,
        description="Peak latency in milliseconds",
    )
    queue_time_ms: float | None = Field(
        default=None,
        description="Average queue time in milliseconds",
    )
    retry_count: int | None = Field(default=None, description="Number of retries")
    timeout_count: int | None = Field(default=None, description="Number of timeouts")
    data_processed_bytes: int | None = Field(
        default=None,
        description="Total data processed in bytes",
    )
    parallel_executions: int | None = Field(
        default=None,
        description="Number of parallel executions",
    )
    cache_hit_rate: float | None = Field(
        default=None,
        description="Cache hit rate percentage",
    )
