"""
Event model for subscription failure.

Published when a subscription fails to be created,
used for error tracking and retry coordination.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import Field

from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelSubscriptionFailedEvent", "SUBSCRIPTION_FAILED_EVENT"]

SUBSCRIPTION_FAILED_EVENT = "onex.runtime.subscription.failed"


class ModelSubscriptionFailedEvent(ModelRuntimeEventBase):
    """
    Event published when a subscription fails to be created.

    Used for error tracking and retry coordination.
    """

    event_type: str = Field(
        default=SUBSCRIPTION_FAILED_EVENT,
        description="Event type identifier",
    )
    node_id: UUID = Field(
        default=...,
        description="Node that attempted to subscribe",
    )
    topic: str = Field(
        default=...,
        description="Topic that failed to be subscribed to",
    )
    error_code: str = Field(
        default=...,
        description="Error code identifying the failure type",
    )
    error_message: str = Field(
        default=...,
        description="Human-readable error description",
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retry attempts made",
    )
    retryable: bool = Field(
        default=True,
        description="Whether this error is retryable",
    )
    failed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the failure occurred (UTC)",
    )

    @classmethod
    def create(
        cls,
        node_id: UUID,
        topic: str,
        error_code: str,
        error_message: str,
        *,
        retry_count: int = 0,
        retryable: bool = True,
        correlation_id: UUID | None = None,
    ) -> "ModelSubscriptionFailedEvent":
        """Factory method for creating a subscription failed event."""
        return cls(
            node_id=node_id,
            topic=topic,
            error_code=error_code,
            error_message=error_message,
            retry_count=retry_count,
            retryable=retryable,
            correlation_id=correlation_id,
        )
