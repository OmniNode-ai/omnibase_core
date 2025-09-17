"""
Usage metrics model for LLM operations.

Tracks token usage, costs, and performance metrics
across all LLM providers for monitoring and optimization.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelUsageMetrics(BaseModel):
    """
    Usage and performance metrics for LLM operations.

    Captures token usage, cost tracking, and performance
    metrics across all providers for comprehensive monitoring
    and optimization capabilities.
    """

    prompt_tokens: int = Field(ge=0, description="Number of tokens in the input prompt")

    completion_tokens: int = Field(
        ge=0,
        description="Number of tokens in the generated response",
    )

    total_tokens: int = Field(
        ge=0,
        description="Total tokens used (prompt + completion)",
    )

    cost_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="Cost in USD for this operation (0.0 for local models)",
    )

    latency_ms: int = Field(ge=0, description="Response latency in milliseconds")

    throughput_tokens_per_second: float | None = Field(
        default=None,
        ge=0.0,
        description="Generation throughput in tokens per second",
    )

    context_length_used: int | None = Field(
        default=None,
        ge=0,
        description="Amount of context window used",
    )

    context_length_available: int | None = Field(
        default=None,
        ge=0,
        description="Total context window available",
    )

    cache_hit: bool = Field(
        default=False,
        description="Whether response was served from cache",
    )

    provider_specific_metrics: dict = Field(
        default_factory=dict,
        description="Provider-specific performance metrics",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "prompt_tokens": 45,
                "completion_tokens": 234,
                "total_tokens": 279,
                "cost_usd": 0.000558,
                "latency_ms": 1250,
                "throughput_tokens_per_second": 18.7,
                "context_length_used": 1024,
                "context_length_available": 4096,
                "cache_hit": False,
                "provider_specific_metrics": {
                    "model_load_time_ms": 45,
                    "gpu_utilization": 0.75,
                    "memory_usage_mb": 2048,
                },
            },
        },
    )

    @property
    def context_utilization(self) -> float | None:
        """Calculate context window utilization percentage."""
        if self.context_length_used and self.context_length_available:
            return self.context_length_used / self.context_length_available
        return None

    @property
    def cost_per_token(self) -> float:
        """Calculate cost per token."""
        if self.total_tokens > 0:
            return self.cost_usd / self.total_tokens
        return 0.0

    def add_provider_metric(self, key: str, value: Any) -> None:
        """Add a provider-specific metric."""
        self.provider_specific_metrics[key] = value
