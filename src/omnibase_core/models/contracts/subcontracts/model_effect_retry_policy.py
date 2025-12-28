"""
Effect Retry Policy Model.

Retry policy with idempotency awareness for effect operations.
Defines configurable retry behavior including backoff strategies,
retryable status codes, and error handling.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants import TIMEOUT_DEFAULT_MS, TIMEOUT_LONG_MS, TIMEOUT_MIN_MS

__all__ = ["ModelEffectRetryPolicy"]


class ModelEffectRetryPolicy(BaseModel):
    """
    Retry policy configuration for effect operations with idempotency awareness.

    Defines configurable retry behavior including backoff strategies, retryable
    status codes, and error handling. Retries are ONLY safe for idempotent
    operations - non-idempotent operations with retry enabled will fail validation.

    Backoff Strategies:
        - fixed: Constant delay between retries (base_delay_ms)
        - exponential: Delay doubles each retry (base_delay_ms * 2^attempt)
        - linear: Delay increases linearly (base_delay_ms * attempt)

    All strategies apply jitter (±jitter_factor * delay) to prevent thundering herd.

    Attributes:
        enabled: Whether retry is enabled for this operation. Defaults to True.
        max_retries: Maximum number of retry attempts (0-10). Default: 3.
        backoff_strategy: Strategy for calculating delay between retries.
            Options: "fixed", "exponential", "linear". Default: "exponential".
        base_delay_ms: Initial delay between retries in milliseconds (100-60000ms).
            Default: 1000ms.
        max_delay_ms: Maximum delay cap for exponential/linear backoff
            (TIMEOUT_MIN_MS-TIMEOUT_LONG_MS). Default: TIMEOUT_DEFAULT_MS.
            See omnibase_core.constants for timeout constant values.
        jitter_factor: Randomization factor as fraction of delay (0.0-0.5).
            Default: 0.1 (10% jitter).
        retryable_status_codes: HTTP status codes that trigger retry.
            Default: [429, 500, 502, 503, 504].
        retryable_errors: Error codes that trigger retry (e.g., network errors).
            Default: ["ECONNRESET", "ETIMEDOUT", "ECONNREFUSED"].

    Example:
        >>> policy = ModelEffectRetryPolicy(
        ...     enabled=True,
        ...     max_retries=3,
        ...     backoff_strategy="exponential",
        ...     base_delay_ms=1000,
        ...     jitter_factor=0.1,
        ... )

    See Also:
        - ModelEffectCircuitBreaker: Circuit breaker that works with retry policies
        - IDEMPOTENCY_DEFAULTS: Default idempotency by handler type and operation
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    enabled: bool = Field(default=True)
    max_retries: int = Field(default=3, ge=0, le=10)
    backoff_strategy: Literal["fixed", "exponential", "linear"] = Field(
        default="exponential"
    )
    base_delay_ms: int = Field(default=1000, ge=100, le=60000)
    max_delay_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS, ge=TIMEOUT_MIN_MS, le=TIMEOUT_LONG_MS
    )
    jitter_factor: float = Field(
        default=0.1, ge=0.0, le=0.5, description="Jitter as fraction of delay"
    )
    retryable_status_codes: list[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504]
    )
    retryable_errors: list[str] = Field(
        default_factory=lambda: ["ECONNRESET", "ETIMEDOUT", "ECONNREFUSED"]
    )
