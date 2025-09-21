"""
Retry Policy Model.

Specialized model for handling retry logic with backoff strategies and conditions.

Restructured to use composition of focused sub-models instead of
excessive string fields in a single large model.
"""

from __future__ import annotations

import random
from datetime import datetime

from pydantic import BaseModel, Field

from ...enums.enum_retry_backoff_strategy import RetryBackoffStrategy
from .model_retry_advanced import ModelRetryAdvanced
from .model_retry_conditions import ModelRetryConditions
from .model_retry_config import ModelRetryConfig
from .model_retry_execution import ModelRetryExecution


class ModelRetryPolicy(BaseModel):
    """
    Retry policy configuration model.

    Restructured to use composition of focused sub-models:
    - config: Core retry configuration and backoff settings
    - conditions: Retry trigger conditions and decision logic
    - execution: Execution tracking and state management
    - advanced: Circuit breaker and advanced features
    """

    # Composed sub-models for focused concerns
    config: ModelRetryConfig = Field(
        default_factory=ModelRetryConfig,
        description="Core retry configuration",
    )
    conditions: ModelRetryConditions = Field(
        default_factory=ModelRetryConditions,
        description="Retry conditions and triggers",
    )
    execution: ModelRetryExecution = Field(
        default_factory=ModelRetryExecution,
        description="Execution tracking and state",
    )
    advanced: ModelRetryAdvanced = Field(
        default_factory=ModelRetryAdvanced,
        description="Advanced features and metadata",
    )

    # Backward compatibility properties
    @property
    def max_retries(self) -> int:
        """Get max retries from config."""
        return self.config.max_retries

    @property
    def current_attempt(self) -> int:
        """Get current attempt from execution."""
        return self.execution.current_attempt

    @property
    def backoff_strategy(self) -> RetryBackoffStrategy:
        """Get backoff strategy from config."""
        return self.config.backoff_strategy

    # Delegate properties to appropriate sub-models
    @property
    def has_retries_remaining(self) -> bool:
        """Check if retries are still available."""
        return self.execution.has_attempts_remaining(self.config.max_retries)

    @property
    def is_exhausted(self) -> bool:
        """Check if all retries have been exhausted."""
        return self.execution.is_exhausted(self.config.max_retries)

    @property
    def retry_attempts_made(self) -> int:
        """Get number of retry attempts made (excluding initial attempt)."""
        return self.execution.get_retry_attempts_made()

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        return self.execution.get_success_rate()

    def calculate_next_delay(self) -> float:
        """Calculate delay for next retry attempt."""
        if self.current_attempt == 0:
            return self.config.base_delay_seconds

        delay = self.config.base_delay_seconds

        # Apply backoff strategy
        if self.config.backoff_strategy == RetryBackoffStrategy.FIXED:
            delay = self.config.base_delay_seconds
        elif self.config.backoff_strategy == RetryBackoffStrategy.LINEAR:
            delay = self.config.base_delay_seconds * (
                self.current_attempt * self.config.backoff_multiplier
            )
        elif self.config.backoff_strategy == RetryBackoffStrategy.EXPONENTIAL:
            delay = self.config.base_delay_seconds * (
                self.config.backoff_multiplier**self.current_attempt
            )
        elif self.config.backoff_strategy == RetryBackoffStrategy.FIBONACCI:
            delay = self._calculate_fibonacci_delay()
        elif self.config.backoff_strategy == RetryBackoffStrategy.RANDOM:
            delay = random.uniform(
                self.config.base_delay_seconds, self.config.max_delay_seconds
            )

        # Cap at maximum delay
        delay = min(delay, self.config.max_delay_seconds)

        # Add jitter if enabled
        if self.config.jitter_enabled:
            jitter = random.uniform(
                -self.config.jitter_max_seconds, self.config.jitter_max_seconds
            )
            delay = max(0.1, delay + jitter)

        return delay

    def _calculate_fibonacci_delay(self) -> float:
        """Calculate Fibonacci sequence delay."""

        def fibonacci(n: int) -> int:
            if n <= 1:
                return 1
            return fibonacci(n - 1) + fibonacci(n - 2)

        fib_multiplier = fibonacci(self.current_attempt)
        return self.config.base_delay_seconds * fib_multiplier

    def should_retry(
        self, error: Exception | None = None, status_code: int | None = None
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
            status_code
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
        self.execution.record_attempt(success, error, status_code, execution_time_seconds)

    def get_next_attempt_time(self) -> datetime:
        """Get timestamp for next retry attempt."""
        delay = self.calculate_next_delay()
        return self.execution.get_next_attempt_time(delay)

    def reset(self) -> None:
        """Reset retry policy to initial state."""
        self.execution.reset()

    def get_summary(self) -> dict[str, str | int | bool | float | None]:
        """Get retry policy execution summary."""
        return {
            "max_retries": self.max_retries,
            "current_attempt": self.current_attempt,
            "retry_attempts_made": self.retry_attempts_made,
            "has_retries_remaining": self.has_retries_remaining,
            "is_exhausted": self.is_exhausted,
            "success_rate": self.success_rate,
            "successful_attempt": self.execution.successful_attempt,
            "total_execution_time_seconds": self.execution.total_execution_time_seconds,
            "last_error": self.execution.last_error,
            "last_status_code": self.execution.last_status_code,
            "backoff_strategy": self.backoff_strategy.value,
            "next_delay_seconds": (
                self.calculate_next_delay() if self.has_retries_remaining else None
            ),
        }

    @classmethod
    def create_simple(cls, max_retries: int = 3) -> ModelRetryPolicy:
        """Create simple retry policy with default settings."""
        config = ModelRetryConfig(max_retries=max_retries)
        return cls(config=config)

    @classmethod
    def create_exponential_backoff(
        cls,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
    ) -> ModelRetryPolicy:
        """Create exponential backoff retry policy."""
        config = ModelRetryConfig(
            max_retries=max_retries,
            base_delay_seconds=base_delay,
            max_delay_seconds=max_delay,
            backoff_strategy=RetryBackoffStrategy.EXPONENTIAL,
            backoff_multiplier=multiplier,
        )
        return cls(config=config)

    @classmethod
    def create_fixed_delay(
        cls,
        max_retries: int = 3,
        delay: float = 2.0,
    ) -> ModelRetryPolicy:
        """Create fixed delay retry policy."""
        config = ModelRetryConfig(
            max_retries=max_retries,
            base_delay_seconds=delay,
            max_delay_seconds=delay,
            backoff_strategy=RetryBackoffStrategy.FIXED,
        )
        return cls(config=config)

    @classmethod
    def create_for_http(
        cls,
        max_retries: int = 5,
        base_delay: float = 1.0,
        status_codes: list[int] | None = None,
    ) -> ModelRetryPolicy:
        """Create retry policy optimized for HTTP requests."""
        config = ModelRetryConfig(
            max_retries=max_retries,
            base_delay_seconds=base_delay,
            backoff_strategy=RetryBackoffStrategy.EXPONENTIAL,
            jitter_enabled=True,
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
        """Create retry policy optimized for database operations."""
        config = ModelRetryConfig(
            max_retries=max_retries,
            base_delay_seconds=base_delay,
            backoff_strategy=RetryBackoffStrategy.LINEAR,
            jitter_enabled=True,
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
        config = ModelRetryConfig(max_retries=max_retries)
        advanced = ModelRetryAdvanced.create_with_circuit_breaker(
            circuit_threshold, reset_timeout
        )
        return cls(config=config, advanced=advanced)


# Export for use
__all__ = ["ModelRetryPolicy"]
