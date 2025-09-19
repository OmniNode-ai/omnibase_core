"""
Retry Policy Model.

Specialized model for handling retry logic with backoff strategies and conditions.
"""

import random
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field, field_validator


class RetryBackoffStrategy(Enum):
    """Retry backoff strategy enumeration."""

    FIXED = "fixed"  # Fixed delay between retries
    LINEAR = "linear"  # Linearly increasing delay
    EXPONENTIAL = "exponential"  # Exponentially increasing delay
    RANDOM = "random"  # Random delay within range
    FIBONACCI = "fibonacci"  # Fibonacci sequence delays


class ModelRetryPolicy(BaseModel):
    """
    Retry policy configuration model.

    Provides comprehensive retry logic with various backoff strategies,
    conditional retry logic, and execution tracking.
    """

    # Core retry configuration
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts",
        ge=0,
        le=100,
    )
    base_delay_seconds: float = Field(
        default=1.0,
        description="Base delay between retries in seconds",
        ge=0.1,
        le=3600.0,
    )

    # Backoff strategy
    backoff_strategy: RetryBackoffStrategy = Field(
        default=RetryBackoffStrategy.EXPONENTIAL,
        description="Retry backoff strategy",
    )
    backoff_multiplier: float = Field(
        default=2.0,
        description="Multiplier for exponential/linear backoff",
        ge=1.0,
        le=10.0,
    )
    max_delay_seconds: float = Field(
        default=300.0,
        description="Maximum delay between retries",
        ge=1.0,
        le=3600.0,
    )

    # Jitter configuration
    jitter_enabled: bool = Field(
        default=True,
        description="Whether to add random jitter to delays",
    )
    jitter_max_seconds: float = Field(
        default=1.0,
        description="Maximum jitter to add/subtract",
        ge=0.0,
        le=60.0,
    )

    # Retry conditions
    retry_on_exceptions: list[str] = Field(
        default_factory=lambda: ["ConnectionError", "TimeoutError", "HTTPError"],
        description="Exception types that should trigger retries",
    )
    retry_on_status_codes: list[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504],
        description="HTTP status codes that should trigger retries",
    )
    stop_on_success: bool = Field(
        default=True,
        description="Whether to stop retrying on success",
    )

    # Execution tracking
    current_attempt: int = Field(
        default=0,
        description="Current retry attempt number",
        ge=0,
    )
    last_attempt_time: datetime | None = Field(
        default=None,
        description="Timestamp of last retry attempt",
    )
    last_error: str | None = Field(
        default=None,
        description="Last error message encountered",
    )
    last_status_code: int | None = Field(
        default=None,
        description="Last HTTP status code encountered",
    )

    # Success tracking
    total_execution_time_seconds: float = Field(
        default=0.0,
        description="Total time spent across all attempts",
        ge=0.0,
    )
    successful_attempt: int | None = Field(
        default=None,
        description="Attempt number that succeeded (if any)",
    )

    # Advanced configuration
    circuit_breaker_enabled: bool = Field(
        default=False,
        description="Whether to enable circuit breaker pattern",
    )
    circuit_breaker_threshold: int = Field(
        default=5,
        description="Consecutive failures before opening circuit",
        ge=1,
    )
    circuit_breaker_reset_timeout_seconds: float = Field(
        default=60.0,
        description="Time before attempting to close circuit",
        ge=1.0,
    )

    # Metadata
    description: str | None = Field(
        default=None,
        description="Human-readable policy description",
    )
    custom_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom retry policy metadata",
    )

    @field_validator("max_delay_seconds")
    @classmethod
    def validate_max_delay(cls, v: float, info: Any) -> float:
        """Validate max delay is greater than base delay."""
        if "base_delay_seconds" in info.data:
            base = info.data["base_delay_seconds"]
            if v < base:
                msg = "Max delay must be greater than or equal to base delay"
                raise ValueError(msg)
        return v

    @field_validator("current_attempt")
    @classmethod
    def validate_current_attempt(cls, v: int, info: Any) -> int:
        """Validate current attempt doesn't exceed max retries."""
        if "max_retries" in info.data:
            max_retries = info.data["max_retries"]
            if v > max_retries:
                msg = "Current attempt cannot exceed max retries"
                raise ValueError(msg)
        return v

    @property
    def has_retries_remaining(self) -> bool:
        """Check if retries are still available."""
        return self.current_attempt < self.max_retries

    @property
    def is_exhausted(self) -> bool:
        """Check if all retries have been exhausted."""
        return self.current_attempt >= self.max_retries

    @property
    def retry_attempts_made(self) -> int:
        """Get number of retry attempts made (excluding initial attempt)."""
        return max(0, self.current_attempt - 1)

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.current_attempt == 0:
            return 0.0
        if self.successful_attempt is not None:
            return 100.0
        return 0.0

    def calculate_next_delay(self) -> float:
        """Calculate delay for next retry attempt."""
        if self.current_attempt == 0:
            return self.base_delay_seconds

        delay = self.base_delay_seconds

        # Apply backoff strategy
        if self.backoff_strategy == RetryBackoffStrategy.FIXED:
            delay = self.base_delay_seconds
        elif self.backoff_strategy == RetryBackoffStrategy.LINEAR:
            delay = self.base_delay_seconds * (
                self.current_attempt * self.backoff_multiplier
            )
        elif self.backoff_strategy == RetryBackoffStrategy.EXPONENTIAL:
            delay = self.base_delay_seconds * (
                self.backoff_multiplier**self.current_attempt
            )
        elif self.backoff_strategy == RetryBackoffStrategy.FIBONACCI:
            delay = self._calculate_fibonacci_delay()
        elif self.backoff_strategy == RetryBackoffStrategy.RANDOM:
            delay = random.uniform(self.base_delay_seconds, self.max_delay_seconds)

        # Cap at maximum delay
        delay = min(delay, self.max_delay_seconds)

        # Add jitter if enabled
        if self.jitter_enabled:
            jitter = random.uniform(-self.jitter_max_seconds, self.jitter_max_seconds)
            delay = max(0.1, delay + jitter)

        return delay

    def _calculate_fibonacci_delay(self) -> float:
        """Calculate Fibonacci sequence delay."""

        def fibonacci(n: int) -> int:
            if n <= 1:
                return 1
            return fibonacci(n - 1) + fibonacci(n - 2)

        fib_multiplier = fibonacci(self.current_attempt)
        return self.base_delay_seconds * fib_multiplier

    def should_retry(
        self, error: Exception | None = None, status_code: int | None = None
    ) -> bool:
        """Determine if retry should be attempted."""
        # Check if retries exhausted
        if self.is_exhausted:
            return False

        # Check error conditions
        if error is not None:
            error_type = type(error).__name__
            if self.retry_on_exceptions and error_type not in self.retry_on_exceptions:
                return False

        # Check status code conditions
        if status_code is not None:
            if (
                self.retry_on_status_codes
                and status_code not in self.retry_on_status_codes
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
        self.current_attempt += 1
        self.last_attempt_time = datetime.now(UTC)
        self.total_execution_time_seconds += execution_time_seconds

        if error is not None:
            self.last_error = str(error)
        if status_code is not None:
            self.last_status_code = status_code

        if success and self.successful_attempt is None:
            self.successful_attempt = self.current_attempt

    def get_next_attempt_time(self) -> datetime:
        """Get timestamp for next retry attempt."""
        delay = self.calculate_next_delay()
        return datetime.now(UTC) + timedelta(seconds=delay)

    def reset(self) -> None:
        """Reset retry policy to initial state."""
        self.current_attempt = 0
        self.last_attempt_time = None
        self.last_error = None
        self.last_status_code = None
        self.total_execution_time_seconds = 0.0
        self.successful_attempt = None

    def get_summary(self) -> dict[str, Any]:
        """Get retry policy execution summary."""
        return {
            "max_retries": self.max_retries,
            "current_attempt": self.current_attempt,
            "retry_attempts_made": self.retry_attempts_made,
            "has_retries_remaining": self.has_retries_remaining,
            "is_exhausted": self.is_exhausted,
            "success_rate": self.success_rate,
            "successful_attempt": self.successful_attempt,
            "total_execution_time_seconds": self.total_execution_time_seconds,
            "last_error": self.last_error,
            "last_status_code": self.last_status_code,
            "backoff_strategy": self.backoff_strategy.value,
            "next_delay_seconds": (
                self.calculate_next_delay() if self.has_retries_remaining else None
            ),
        }

    @classmethod
    def create_simple(cls, max_retries: int = 3) -> "ModelRetryPolicy":
        """Create simple retry policy with default settings."""
        return cls(max_retries=max_retries)

    @classmethod
    def create_exponential_backoff(
        cls,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
    ) -> "ModelRetryPolicy":
        """Create exponential backoff retry policy."""
        return cls(
            max_retries=max_retries,
            base_delay_seconds=base_delay,
            max_delay_seconds=max_delay,
            backoff_strategy=RetryBackoffStrategy.EXPONENTIAL,
            backoff_multiplier=multiplier,
        )

    @classmethod
    def create_fixed_delay(
        cls,
        max_retries: int = 3,
        delay: float = 2.0,
    ) -> "ModelRetryPolicy":
        """Create fixed delay retry policy."""
        return cls(
            max_retries=max_retries,
            base_delay_seconds=delay,
            max_delay_seconds=delay,
            backoff_strategy=RetryBackoffStrategy.FIXED,
        )

    @classmethod
    def create_for_http(
        cls,
        max_retries: int = 5,
        base_delay: float = 1.0,
        status_codes: list[int] | None = None,
    ) -> "ModelRetryPolicy":
        """Create retry policy optimized for HTTP requests."""
        if status_codes is None:
            status_codes = [429, 500, 502, 503, 504]

        return cls(
            max_retries=max_retries,
            base_delay_seconds=base_delay,
            backoff_strategy=RetryBackoffStrategy.EXPONENTIAL,
            retry_on_status_codes=status_codes,
            jitter_enabled=True,
        )

    @classmethod
    def create_for_database(
        cls,
        max_retries: int = 3,
        base_delay: float = 0.5,
    ) -> "ModelRetryPolicy":
        """Create retry policy optimized for database operations."""
        return cls(
            max_retries=max_retries,
            base_delay_seconds=base_delay,
            backoff_strategy=RetryBackoffStrategy.LINEAR,
            retry_on_exceptions=[
                "DatabaseError",
                "ConnectionError",
                "OperationalError",
            ],
            jitter_enabled=True,
        )


# Export for use
__all__ = ["ModelRetryPolicy", "RetryBackoffStrategy"]
