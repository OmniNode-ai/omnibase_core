"""
Retry performance models.

Provides typed models for retry configuration performance data,
replacing dict[str, Any] return types in ModelRetryConfig methods.
"""

from pydantic import BaseModel, Field

# Re-export from split module
from .model_circuit_breaker_recommendation import ModelCircuitBreakerRecommendation


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


__all__ = ["ModelRetryPerformanceImpact", "ModelCircuitBreakerRecommendation"]
