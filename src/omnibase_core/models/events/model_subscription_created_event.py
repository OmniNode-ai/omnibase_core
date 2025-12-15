"""
Event model for subscription creation.

Published when a subscription is successfully created,
confirming a node has been wired to an event bus topic.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import Field

from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelSubscriptionCreatedEvent", "SUBSCRIPTION_CREATED_EVENT"]

SUBSCRIPTION_CREATED_EVENT = "onex.runtime.subscription.created"


class ModelSubscriptionCreatedEvent(ModelRuntimeEventBase):
    """
    Event published when a subscription is successfully created.

    Confirms that a node has been wired to an event bus topic.
    """

    event_type: str = Field(
        default=SUBSCRIPTION_CREATED_EVENT,
        description="Event type identifier",
    )
    subscription_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this subscription",
    )
    node_id: UUID = Field(
        default=...,
        description="Node that owns this subscription",
    )
    topic: str = Field(
        default=...,
        description="Topic the node is subscribed to",
    )
    handler_name: str | None = Field(
        default=None,
        description="Name of the handler method for this subscription",
    )
    subscribed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the subscription was created (UTC)",
    )
    event_bus_type: str = Field(
        default="inmemory",
        description="Type of event bus (inmemory, kafka, etc.)",
    )

    @classmethod
    def create(
        cls,
        node_id: UUID,
        topic: str,
        *,
        subscription_id: UUID | None = None,
        handler_name: str | None = None,
        correlation_id: UUID | None = None,
        event_bus_type: str = "inmemory",
    ) -> "ModelSubscriptionCreatedEvent":
        """Factory method for creating a subscription created event."""
        return cls(
            subscription_id=subscription_id or uuid4(),
            node_id=node_id,
            topic=topic,
            handler_name=handler_name,
            correlation_id=correlation_id,
            event_bus_type=event_bus_type,
        )
