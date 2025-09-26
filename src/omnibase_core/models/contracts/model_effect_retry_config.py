"""
Effect Retry Configuration Model.

Defines retry strategies, backoff algorithms, and circuit
breaker patterns for resilient side-effect operations.
"""

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class ModelEffectRetryConfig(BaseModel):
    """
    Retry policies and circuit breaker configuration.

    Defines retry strategies, backoff algorithms, and circuit
    breaker patterns for resilient side-effect operations.
    """

    max_attempts: int = Field(default=3, description="Maximum retry attempts", ge=1)

    backoff_strategy: str = Field(
        default="exponential",
        description="Backoff strategy (linear, exponential, constant)",
    )

    base_delay_ms: int = Field(
        default=100,
        description="Base delay between retries in milliseconds",
        ge=1,
    )

    max_delay_ms: int = Field(
        default=5000,
        description="Maximum delay between retries in milliseconds",
        ge=1,
    )

    jitter_enabled: bool = Field(
        default=True,
        description="Enable jitter in retry delays",
    )

    circuit_breaker_enabled: bool = Field(
        default=True,
        description="Enable circuit breaker pattern",
    )

    circuit_breaker_threshold: int = Field(
        default=3,
        description="Circuit breaker failure threshold",
        ge=1,
    )

    circuit_breaker_timeout_s: int = Field(
        default=60,
        description="Circuit breaker timeout in seconds",
        ge=1,
    )

    @field_validator("max_delay_ms")
    @classmethod
    def validate_max_delay_greater_than_base(
        cls,
        v: int,
        info: ValidationInfo,
    ) -> int:
        """Validate max_delay_ms is greater than base_delay_ms."""
        if "base_delay_ms" in info.data and v <= info.data["base_delay_ms"]:
            msg = "max_delay_ms must be greater than base_delay_ms"
            raise ValueError(msg)
        return v

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


__all__ = ["ModelEffectRetryConfig"]
