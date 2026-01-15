"""
Effect Retry Configuration Model.

Defines retry strategies, backoff algorithms, and circuit
breaker patterns for resilient side-effect operations.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_retry_backoff_strategy import EnumRetryBackoffStrategy
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelEffectRetryConfig(BaseModel):
    """
    Retry policies and circuit breaker configuration.

    Defines retry strategies, backoff algorithms, and circuit
    breaker patterns for resilient side-effect operations.
    """

    max_attempts: int = Field(default=3, description="Maximum retry attempts", ge=1)

    backoff_strategy: EnumRetryBackoffStrategy = Field(
        default=EnumRetryBackoffStrategy.EXPONENTIAL,
        description="Backoff strategy (fixed, linear, exponential, random, fibonacci)",
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

    @model_validator(mode="after")
    def validate_max_delay_greater_than_base(self) -> Self:
        """
        Validate that max_delay_ms is greater than base_delay_ms.

        Ensures the maximum retry delay is always greater than the base delay
        to maintain valid backoff progression. This validation prevents
        configuration errors that would result in invalid backoff calculations.

        Returns:
            The validated model instance if validation passes.

        Raises:
            ModelOnexError: If max_delay_ms is less than or equal to base_delay_ms.
                Error includes validation context and error type metadata.

        Example:
            ```python
            # Valid configuration - max_delay > base_delay
            config = ModelEffectRetryConfig(
                base_delay_ms=100,
                max_delay_ms=5000  # Valid: 5000 > 100
            )

            # Invalid configuration - raises ModelOnexError
            try:
                config = ModelEffectRetryConfig(
                    base_delay_ms=5000,
                    max_delay_ms=1000  # Invalid: 1000 <= 5000
                )
            except ModelOnexError as e:
                print(f"Validation failed: {e.message}")
            ```

        Note:
            This validator is automatically called during model instantiation
            and when max_delay_ms is assigned to an existing instance with
            validate_assignment=True. Uses @model_validator(mode='after') to
            ensure both fields are always available (no fallback pattern).
        """
        if self.max_delay_ms <= self.base_delay_ms:
            msg = "max_delay_ms must be greater than base_delay_ms"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                error_type="valueerror",
                validation_context="model_validation",
            )
        return self

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


__all__ = ["ModelEffectRetryConfig"]
