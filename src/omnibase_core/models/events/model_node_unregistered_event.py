"""
Event model for node unregistration.

Published when a node is unregistered from the runtime,
triggers subscription cleanup.
"""

from uuid import UUID

from pydantic import Field

from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelNodeUnregisteredEvent", "NODE_UNREGISTERED_EVENT"]

NODE_UNREGISTERED_EVENT = "onex.runtime.node.unregistered"


class ModelNodeUnregisteredEvent(ModelRuntimeEventBase):
    """
    Event published when a node is unregistered from the runtime.

    Triggers subscription cleanup for removed nodes.
    """

    event_type: str = Field(
        default=NODE_UNREGISTERED_EVENT,
        description="Event type identifier",
    )
    node_id: UUID = Field(
        default=...,
        description="Unique identifier of the unregistered node",
    )
    node_name: str = Field(
        default=...,
        description="Human-readable name of the node",
    )
    reason: str = Field(
        default="unregistered",
        description="Reason for unregistration (graceful, error, forced)",
    )
    active_subscriptions: list[str] = Field(
        default_factory=list,
        description="Topics this node was subscribed to (for cleanup)",
    )

    @classmethod
    def create(
        cls,
        node_id: UUID,
        node_name: str,
        *,
        reason: str = "unregistered",
        correlation_id: UUID | None = None,
        active_subscriptions: list[str] | None = None,
    ) -> "ModelNodeUnregisteredEvent":
        """Factory method for creating a node unregistered event."""
        return cls(
            node_id=node_id,
            node_name=node_name,
            reason=reason,
            correlation_id=correlation_id,
            active_subscriptions=(
                active_subscriptions if active_subscriptions is not None else []
            ),
        )
