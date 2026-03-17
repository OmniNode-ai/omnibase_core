# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Event model for subscription creation.

Published when a subscription is successfully created,
confirming a node has been wired to an event bus topic.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from omnibase_core.enums.enum_event_bus_type import EnumEventBusType
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
    event_bus_type: EnumEventBusType = Field(
        description="Type of event bus being used (KAFKA, CLOUD, or INMEMORY). Required — no silent default.",
    )
    env: str = Field(
        default="development",
        description="Deployment environment (development, staging, production).",
    )

    @model_validator(mode="after")
    def forbid_inmemory_in_production(self) -> "ModelSubscriptionCreatedEvent":
        """Raise ValueError if bus_type is INMEMORY and env is production."""
        env_normalized = (self.env or "").strip().lower()
        if (
            self.event_bus_type == EnumEventBusType.INMEMORY
            and env_normalized == "production"
        ):
            msg = (
                "EnumEventBusType.INMEMORY is forbidden in production. "
                "Use EnumEventBusType.KAFKA or EnumEventBusType.CLOUD."
            )
            raise ValueError(msg)
        return self

    @classmethod
    def create(
        cls,
        node_id: UUID,
        topic: str,
        *,
        subscription_id: UUID | None = None,
        handler_name: str | None = None,
        correlation_id: UUID | None = None,
        event_bus_type: EnumEventBusType,
        env: str = "development",
    ) -> "ModelSubscriptionCreatedEvent":
        """Factory method for creating a subscription created event."""
        return cls(
            subscription_id=subscription_id or uuid4(),
            node_id=node_id,
            topic=topic,
            handler_name=handler_name,
            correlation_id=correlation_id,
            event_bus_type=event_bus_type,
            env=env,
        )
