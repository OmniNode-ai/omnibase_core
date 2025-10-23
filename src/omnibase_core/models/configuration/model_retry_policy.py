from pydantic import Field

"""
Retry Policy Model.

Type-safe retry policy configuration for handling failures
in distributed operations.
"""

from pydantic import BaseModel


class ModelRetryPolicy(BaseModel):
    """
    Retry policy configuration.

    Provides structured retry behavior for handling failures
    in distributed operations with backoff strategies.
    """

    max_attempts: int = Field(
        default=3,
        description="Maximum retry attempts",
        ge=0,
        le=10,
    )
    initial_delay_ms: int = Field(
        default=1000,
        description="Initial delay in milliseconds",
        ge=0,
    )
    max_delay_ms: int = Field(
        default=30000,
        description="Maximum delay in milliseconds",
        ge=0,
    )
    backoff_multiplier: float = Field(
        default=2.0,
        description="Backoff multiplier for exponential backoff",
        ge=1.0,
        le=10.0,
    )
    jitter_enabled: bool = Field(
        default=True,
        description="Whether to add random jitter to delays",
    )
    retryable_errors: list[str] = Field(
        default_factory=lambda: ["timeout", "network_error", "service_unavailable"],
        description="List of retryable error types",
    )
    non_retryable_errors: list[str] = Field(
        default_factory=lambda: [
            "authentication_error",
            "authorization_error",
            "not_found",
        ],
        description="List of non-retryable error types",
    )
    circuit_breaker_enabled: bool = Field(
        default=False,
        description="Whether circuit breaker is enabled",
    )

    def should_retry(self, attempt: int, error_type: str) -> bool:
        """Check if operation should be retried."""
        if attempt >= self.max_attempts:
            return False

        if error_type in self.non_retryable_errors:
            return False

        return not (self.retryable_errors and error_type not in self.retryable_errors)

    def get_delay_ms(self, attempt: int) -> int:
        """Calculate delay for given attempt number."""
        if attempt <= 0:
            return 0

        delay = self.initial_delay_ms * (self.backoff_multiplier ** (attempt - 1))
        delay = min(delay, self.max_delay_ms)

        if self.jitter_enabled:
            import random

            jitter = random.uniform(0.8, 1.2)
            delay = int(delay * jitter)

        return int(delay)
