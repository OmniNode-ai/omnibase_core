"""
Retry performance models.

Provides typed models for retry configuration performance data,
replacing dict[str, Any] return types in ModelRetryConfig methods.
"""

from pydantic import BaseModel, Field


class ModelRetryPerformanceImpact(BaseModel):
    """
    Typed model for retry performance impact assessment.

    Replaces dict[str, str] return from get_performance_impact() in ModelRetryConfig.
    """

    latency_impact: str = Field(
        default="minimal",
        description="Latency impact level (minimal, moderate, high)",
    )
    resource_impact: str = Field(
        default="low",
        description="Resource impact level (low, moderate, high)",
    )
    backoff_efficiency: str = Field(
        default="high",
        description="Backoff efficiency rating (moderate, high)",
    )
    total_retry_time: str = Field(
        default="0.0s",
        description="Total retry time as formatted string",
    )
    strategy_type: str = Field(
        default="conservative_exponential",
        description="Retry strategy classification",
    )


class ModelCircuitBreakerRecommendation(BaseModel):
    """
    Typed model for circuit breaker recommendation data.

    Replaces dict[str, Any] return from get_circuit_breaker_recommendations() in ModelRetryConfig.
    """

    recommended: bool = Field(
        default=False,
        description="Whether circuit breaker is recommended",
    )
    reason: str = Field(
        default="",
        description="Reason for the recommendation",
    )
    failure_threshold: int | None = Field(
        default=None,
        description="Recommended failure threshold",
        ge=1,
    )
    timeout_seconds: int | None = Field(
        default=None,
        description="Recommended timeout in seconds",
        ge=1,
    )
    half_open_max_calls: int | None = Field(
        default=None,
        description="Recommended max calls in half-open state",
        ge=1,
    )


__all__ = ["ModelRetryPerformanceImpact", "ModelCircuitBreakerRecommendation"]
