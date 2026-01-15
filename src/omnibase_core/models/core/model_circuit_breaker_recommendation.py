"""Circuit breaker recommendation model."""

from pydantic import BaseModel, Field


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
