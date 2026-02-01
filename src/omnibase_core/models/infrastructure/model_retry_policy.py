"""
Retry Policy Model.

Specialized model for handling retry logic with backoff strategies and conditions.

Restructured to use composition of focused sub-models instead of
excessive string fields in a single large model.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_retry_backoff_strategy import EnumRetryBackoffStrategy
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_retry_config import ModelRetryConfig
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

from .model_retry_advanced import ModelRetryAdvanced
from .model_retry_conditions import ModelRetryConditions
from .model_retry_execution import ModelRetryExecution


class ModelRetryPolicy(BaseModel):
    """
    Retry policy configuration model.

    Restructured to use composition of focused sub-models:
    - config: Core retry configuration and backoff settings
    - conditions: Retry trigger conditions and decision logic
    - execution: Execution tracking and state management
    - advanced: Circuit breaker and advanced features
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    # Composed sub-models for focused concerns
    config: ModelRetryConfig = Field(
        default_factory=lambda: ModelRetryConfig(),
        description="Core retry configuration",
    )
    conditions: ModelRetryConditions = Field(
        default_factory=lambda: ModelRetryConditions(),
        description="Retry conditions and triggers",
    )
    execution: ModelRetryExecution = Field(
        default_factory=lambda: ModelRetryExecution(),
        description="Execution tracking and state",
    )
    advanced: ModelRetryAdvanced = Field(
        default_factory=lambda: ModelRetryAdvanced(),
        description="Advanced features and metadata",
    )

    # Delegation properties
    @property
    def max_retries(self) -> int:
        """Get max retries from config."""
        return self.config.max_attempts

    @property
    def current_attempt(self) -> int:
        """Get current attempt from execution."""
        return self.execution.current_attempt

    @property
    def backoff_strategy(self) -> EnumRetryBackoffStrategy:
        """Get backoff strategy from config."""
        # Map bool-based API to enum representation
        return (
            EnumRetryBackoffStrategy.EXPONENTIAL
            if self.config.exponential_backoff
            else EnumRetryBackoffStrategy.LINEAR
        )

    # Delegate properties to appropriate sub-models
    @property
    def can_attempt_retry(self) -> bool:
        """Check if retries are still available."""
        return self.execution.can_retry(self.config.max_attempts)

    @property
    def is_exhausted(self) -> bool:
        """Check if all retries have been exhausted."""
        return self.execution.is_exhausted(self.config.max_attempts)

    @property
    def retry_attempts_made(self) -> int:
        """Get number of retry attempts made (excluding initial attempt)."""
        return self.execution.get_retry_attempts_made()

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        return self.execution.get_success_rate()

    @property
    def has_retries_remaining(self) -> bool:
        """Check if retries are still available."""
        return self.can_attempt_retry

    def calculate_next_delay(self) -> float:
        """Calculate delay for next retry attempt."""
        if self.current_attempt == 0:
            return self.config.backoff_seconds

        # Delegate to config's built-in delay calculation
        # Note: config.calculate_delay() expects 1-based attempt numbers
        # and already includes jitter by default
        return self.config.calculate_delay(
            attempt_number=self.current_attempt,
            include_jitter=True,
        )

    def should_retry(
        self,
        error: Exception | None = None,
        status_code: int | None = None,
    ) -> bool:
        """Determine if retry should be attempted."""
        # Check if retries exhausted
        if self.is_exhausted:
            return False

        # Check error conditions
        if error is not None and not self.conditions.should_retry_exception(error):
            return False

        # Check status code conditions
        if status_code is not None and not self.conditions.should_retry_status_code(
            status_code,
        ):
            return False

        return True

    def record_attempt(
        self,
        success: bool = False,
        error: Exception | None = None,
        status_code: int | None = None,
        execution_time_seconds: float = 0.0,
    ) -> None:
        """Record the result of an attempt."""
        self.execution.record_attempt(
            success,
            error,
            status_code if status_code is not None else 0,
            execution_time_seconds,
        )

    def get_next_attempt_time(self) -> datetime:
        """Get timestamp for next retry attempt."""
        delay = self.calculate_next_delay()
        return self.execution.get_next_attempt_time(delay)

    def reset(self) -> None:
        """Reset retry policy to initial state."""
        self.execution.reset()

    def get_summary(self) -> dict[str, ModelSchemaValue]:
        """Get retry policy execution summary using proper ModelSchemaValue types."""
        return {
            "max_retries": ModelSchemaValue.from_value(self.max_retries),
            "current_attempt": ModelSchemaValue.from_value(self.current_attempt),
            "retry_attempts_made": ModelSchemaValue.from_value(
                self.retry_attempts_made,
            ),
            "has_retries_remaining": ModelSchemaValue.from_value(
                self.has_retries_remaining,
            ),
            "is_exhausted": ModelSchemaValue.from_value(self.is_exhausted),
            "success_rate": ModelSchemaValue.from_value(self.success_rate),
            "successful_attempt": ModelSchemaValue.from_value(
                self.execution.successful_attempt,
            ),
            "total_execution_time_seconds": ModelSchemaValue.from_value(
                self.execution.total_execution_time_seconds,
            ),
            "last_error": ModelSchemaValue.from_value(
                (
                    str(self.execution.error_message.to_value())
                    if self.execution.error_message.to_value()
                    else None
                ),
            ),
            "last_status_code": ModelSchemaValue.from_value(
                self.execution.last_status_code,
            ),
            "backoff_strategy": ModelSchemaValue.from_value(
                self.backoff_strategy.value,
            ),
            "next_delay_seconds": ModelSchemaValue.from_value(
                self.calculate_next_delay() if self.has_retries_remaining else None,
            ),
        }

    @classmethod
    def create_simple(cls, max_retries: int = 3) -> ModelRetryPolicy:
        """Create simple retry policy with default settings."""
        config = ModelRetryConfig(max_attempts=max_retries)
        return cls(config=config)

    @classmethod
    def create_exponential_backoff(
        cls,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
    ) -> ModelRetryPolicy:
        """Create exponential backoff retry policy.

        Note: max_delay and multiplier parameters are accepted for backwards
        compatibility but are not used in the new API. The multiplier is
        hardcoded to 2 in the new implementation.
        """
        config = ModelRetryConfig(
            max_attempts=max_retries,
            backoff_seconds=base_delay,
            exponential_backoff=True,
        )
        return cls(config=config)

    @classmethod
    def create_fixed_delay(
        cls,
        max_retries: int = 3,
        delay: float = 2.0,
    ) -> ModelRetryPolicy:
        """Create fixed delay retry policy.

        Note: Uses linear backoff with max_attempts=1 to simulate fixed delay.
        For true fixed delay, consider using exponential_backoff=False with
        backoff_seconds set to your desired delay.
        """
        config = ModelRetryConfig(
            max_attempts=max_retries,
            backoff_seconds=delay,
            exponential_backoff=False,
        )
        return cls(config=config)

    @classmethod
    def create_for_http(
        cls,
        max_retries: int = 5,
        base_delay: float = 1.0,
        status_codes: list[int] | None = None,
    ) -> ModelRetryPolicy:
        """Create retry policy optimized for HTTP requests.

        Note: Jitter is always enabled in the new API via the calculate_delay()
        method's include_jitter parameter.
        """
        config = ModelRetryConfig(
            max_attempts=max_retries,
            backoff_seconds=base_delay,
            exponential_backoff=True,
        )
        conditions = ModelRetryConditions.create_http_only()
        if status_codes:
            conditions.retry_on_status_codes = status_codes
        return cls(config=config, conditions=conditions)

    @classmethod
    def create_for_database(
        cls,
        max_retries: int = 3,
        base_delay: float = 0.5,
    ) -> ModelRetryPolicy:
        """Create retry policy optimized for database operations.

        Note: Uses linear backoff (exponential_backoff=False). Jitter is
        always enabled in the new API.
        """
        config = ModelRetryConfig(
            max_attempts=max_retries,
            backoff_seconds=base_delay,
            exponential_backoff=False,
        )
        conditions = ModelRetryConditions.create_database_only()
        return cls(config=config, conditions=conditions)

    @classmethod
    def create_with_circuit_breaker(
        cls,
        max_retries: int = 5,
        circuit_threshold: int = 5,
        reset_timeout: float = 60.0,
    ) -> ModelRetryPolicy:
        """Create retry policy with circuit breaker."""
        config = ModelRetryConfig(max_attempts=max_retries)
        advanced = ModelRetryAdvanced.create_with_circuit_breaker(
            circuit_threshold,
            reset_timeout,
        )
        return cls(config=config, advanced=advanced)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelRetryPolicy"]
