"""
Error handling configuration model for nodes.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.nodes import EnumBackoffStrategy


class ModelErrorHandlingConfig(BaseModel):
    """Error handling configuration."""

    model_config = ConfigDict(extra="forbid")

    retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts",
        ge=0,
    )
    backoff_strategy: EnumBackoffStrategy = Field(
        default=EnumBackoffStrategy.EXPONENTIAL,
        description="Backoff strategy for retries",
    )
    circuit_breaker_enabled: bool = Field(
        default=True,
        description="Enable circuit breaker pattern",
    )
    error_threshold: int = Field(
        default=5,
        description="Error threshold for circuit breaker",
        ge=1,
    )
