"""Retry context model for retry-related metadata.

This module provides ModelRetryContext, a typed context model for tracking
retry attempts, retryability, and next retry scheduling.

Thread Safety:
    ModelRetryContext instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access across multiple threads.

See Also:
    - ModelOperationalContext: Operation-level context
    - ModelErrorDetails: Error handling with retry support
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelRetryContext(BaseModel):
    """Typed context for retry-related metadata.

    This model provides structured fields for tracking retry attempts,
    determining retryability, and scheduling next retry times.

    Use Cases:
        - Retry logic in effect nodes
        - Error recovery with exponential backoff
        - Circuit breaker implementations
        - Dead letter queue processing

    Thread Safety:
        Instances are immutable (frozen=True) after creation, making them
        thread-safe for concurrent read access. For pytest-xdist compatibility,
        from_attributes=True is enabled.

    Attributes:
        attempt: Current retry attempt number (1-indexed, 1 = first attempt).
        retryable: Whether this operation can be retried.
        next_retry_at: Scheduled datetime for the next retry attempt.

    Example:
        Retryable error context::

            from omnibase_core.models.context import ModelRetryContext
            from datetime import datetime, timedelta, UTC

            context = ModelRetryContext(
                attempt=2,
                retryable=True,
                next_retry_at=datetime.now(UTC) + timedelta(seconds=30),
            )

        Non-retryable error::

            context = ModelRetryContext(
                attempt=1,
                retryable=False,
            )

    See Also:
        - ModelOperationalContext: For operation metadata
        - ModelErrorDetails: Uses retry context for error handling
    """

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")

    attempt: int = Field(
        default=1,
        description="Current retry attempt number (1-indexed, 1 = first attempt)",
        ge=1,
    )
    retryable: bool = Field(
        default=True,
        description="Whether this operation can be retried",
    )
    next_retry_at: datetime | None = Field(
        default=None,
        description="Scheduled datetime for the next retry attempt",
    )
