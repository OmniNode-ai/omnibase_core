"""
LLM health check response model for providers.

Provides strongly-typed health check responses to replace Dict[str, Any] usage
with proper ONEX naming conventions.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.node import EnumHealthStatus


class ModelLLMHealthResponse(BaseModel):
    """
    Strongly-typed LLM health check response model.

    Replaces Dict[str, Any] usage in provider health_check methods
    with proper type safety and validation.
    """

    status: EnumHealthStatus = Field(description="Health status of the LLM provider")

    latency_ms: int = Field(
        ge=-1,
        description="Response latency in milliseconds (-1 if unavailable)",
    )

    available_models: int = Field(ge=0, description="Number of available models")

    last_check: float = Field(description="Unix timestamp of last health check")

    daily_cost_usd: float | None = Field(
        default=None,
        ge=0.0,
        description="Daily cost in USD (for external providers)",
    )

    error: str | None = Field(
        default=None,
        description="Error message if status is unhealthy",
    )

    version: str | None = Field(
        default=None,
        description="Provider version information",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
