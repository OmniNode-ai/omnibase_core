"""
Event model for subscription removal.

Published when a subscription is removed,
confirming a node has been unwired from an event bus topic.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import Field

from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelSubscriptionRemovedEvent", "SUBSCRIPTION_REMOVED_EVENT"]

SUBSCRIPTION_REMOVED_EVENT = "onex.runtime.subscription.removed"


class ModelSubscriptionRemovedEvent(ModelRuntimeEventBase):
    """
    Event published when a subscription is removed.

    Confirms that a node has been unwired from an event bus topic.
    """

    event_type: str = Field(
        default=SUBSCRIPTION_REMOVED_EVENT,
        description="Event type identifier",
    )
    subscription_id: UUID = Field(
        default=...,
        description="Unique identifier of the removed subscription",
    )
    node_id: UUID = Field(
        default=...,
        description="Node that owned this subscription",
    )
    topic: str = Field(
        default=...,
        description="Topic the node was subscribed to",
    )
    removed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the subscription was removed (UTC)",
    )
    reason: str = Field(
        default="unsubscribed",
        description="Reason for removal (unsubscribed, node_shutdown, error)",
    )

    @classmethod
    def create(
        cls,
        subscription_id: UUID,
        node_id: UUID,
        topic: str,
        *,
        reason: str = "unsubscribed",
        correlation_id: UUID | None = None,
    ) -> "ModelSubscriptionRemovedEvent":
        """Factory method for creating a subscription removed event."""
        return cls(
            subscription_id=subscription_id,
            node_id=node_id,
            topic=topic,
            reason=reason,
            correlation_id=correlation_id,
        )
