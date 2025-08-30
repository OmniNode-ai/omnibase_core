"""
Task Performance Metrics Model

ONEX-compliant task-specific performance metrics model for idle compute tasks.
"""

from pydantic import BaseModel, Field


class ModelTaskPerformanceMetrics(BaseModel):
    """Task-specific performance metrics model with proper typing."""

    throughput_ops_per_second: float = Field(default=0.0, ge=0.0)

    latency_p50_ms: float = Field(default=0.0, ge=0.0)

    latency_p95_ms: float = Field(default=0.0, ge=0.0)

    latency_p99_ms: float = Field(default=0.0, ge=0.0)

    error_rate_percent: float = Field(default=0.0, ge=0.0, le=100.0)

    cache_hit_rate_percent: float = Field(default=0.0, ge=0.0, le=100.0)

    queue_wait_time_ms: float = Field(default=0.0, ge=0.0)

    resource_efficiency_score: float = Field(default=0.0, ge=0.0, le=100.0)
