"""
Event model for node registration.

Published when a new node is registered with the runtime,
used for hot-reload support and subscription wiring.
"""

from uuid import UUID

from pydantic import Field

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelNodeRegisteredEvent", "NODE_REGISTERED_EVENT"]

NODE_REGISTERED_EVENT = "onex.runtime.node.registered"


class ModelNodeRegisteredEvent(ModelRuntimeEventBase):
    """
    Event published when a new node is registered with the runtime.

    Used for hot-reload support to trigger subscription wiring
    for dynamically added nodes.
    """

    event_type: str = Field(
        default=NODE_REGISTERED_EVENT,
        description="Event type identifier",
    )
    node_id: UUID = Field(
        default=...,
        description="Unique identifier of the registered node",
    )
    node_name: str = Field(
        default=...,
        description="Human-readable name of the node",
    )
    node_type: EnumNodeKind = Field(
        default=...,
        description="Type of node (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR)",
    )
    contract_path: str | None = Field(
        default=None,
        description="Path to the node's contract YAML file",
    )
    declared_subscriptions: list[str] = Field(
        default_factory=list,
        description="Topics this node declares subscriptions to",
    )

    @classmethod
    def create(
        cls,
        node_id: UUID,
        node_name: str,
        node_type: EnumNodeKind,
        *,
        correlation_id: UUID | None = None,
        contract_path: str | None = None,
        declared_subscriptions: list[str] | None = None,
    ) -> "ModelNodeRegisteredEvent":
        """Factory method for creating a node registered event."""
        return cls(
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
            correlation_id=correlation_id,
            contract_path=contract_path,
            declared_subscriptions=(
                declared_subscriptions if declared_subscriptions is not None else []
            ),
        )
