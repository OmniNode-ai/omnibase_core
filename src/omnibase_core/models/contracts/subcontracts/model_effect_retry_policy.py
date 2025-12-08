"""
Effect Retry Policy Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Retry policy with idempotency awareness for effect operations.
Defines configurable retry behavior including backoff strategies,
retryable status codes, and error handling.

Implements: OMN-524
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEffectRetryPolicy"]


class ModelEffectRetryPolicy(BaseModel):
    """Retry policy with idempotency awareness."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(default=True)
    max_retries: int = Field(default=3, ge=0, le=10)
    backoff_strategy: Literal["fixed", "exponential", "linear"] = Field(
        default="exponential"
    )
    base_delay_ms: int = Field(default=1000, ge=100, le=60000)
    max_delay_ms: int = Field(default=30000, ge=1000, le=300000)
    jitter_factor: float = Field(
        default=0.1, ge=0.0, le=0.5, description="Jitter as fraction of delay"
    )
    retryable_status_codes: list[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504]
    )
    retryable_errors: list[str] = Field(
        default_factory=lambda: ["ECONNRESET", "ETIMEDOUT", "ECONNREFUSED"]
    )
