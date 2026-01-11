"""
Model for performance metrics tracking.

Captures key performance indicators for the system during the measurement period.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelPerformanceMetrics(BaseModel):
    """Observed performance metrics.

    Captures key performance indicators for the system during the
    measurement period. All latency values are in milliseconds.

    Attributes:
        avg_latency_ms: Average latency in milliseconds.
        p95_latency_ms: 95th percentile latency in milliseconds.
        p99_latency_ms: 99th percentile latency in milliseconds.
        avg_cost_per_call: Average cost per API call.
        total_calls: Total number of calls in the measurement period.
        error_rate: Error rate as a decimal (0.0 to 1.0).

    Example:
        >>> metrics = ModelPerformanceMetrics(
        ...     avg_latency_ms=150.5,
        ...     p95_latency_ms=450.0,
        ...     p99_latency_ms=800.0,
        ...     avg_cost_per_call=0.002,
        ...     total_calls=10000,
        ...     error_rate=0.01
        ... )
        >>> metrics.error_rate
        0.01
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    avg_latency_ms: float = Field(
        ...,
        ge=0.0,
        description="Average latency in milliseconds",
    )
    p95_latency_ms: float = Field(
        ...,
        ge=0.0,
        description="95th percentile latency in milliseconds",
    )
    p99_latency_ms: float = Field(
        ...,
        ge=0.0,
        description="99th percentile latency in milliseconds",
    )
    avg_cost_per_call: float = Field(
        ...,
        ge=0.0,
        description="Average cost per API call",
    )
    total_calls: int = Field(
        ...,
        ge=0,
        description="Total number of calls in the measurement period",
    )
    error_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Error rate as a decimal (0.0 to 1.0)",
    )
