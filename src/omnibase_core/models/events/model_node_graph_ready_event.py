"""
Event model for node graph ready state.

Published when the node graph is fully instantiated,
triggering the event bus wiring process.
"""

from uuid import UUID, uuid4

from pydantic import Field

from omnibase_core.models.events.model_node_graph_info import (
    ModelNodeGraphInfo,
)
from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelNodeGraphReadyEvent", "NODE_GRAPH_READY_EVENT"]

NODE_GRAPH_READY_EVENT = "onex.runtime.node_graph.ready"


class ModelNodeGraphReadyEvent(ModelRuntimeEventBase):
    """
    Event published when the node graph is fully instantiated.

    This event triggers the event bus wiring process to wire
    all nodes to their declared subscriptions.
    """

    event_type: str = Field(
        default=NODE_GRAPH_READY_EVENT,
        description="Event type identifier",
    )
    graph_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this node graph instance",
    )
    node_count: int = Field(
        default=0,
        ge=0,
        description="Total number of nodes in the graph",
    )
    nodes: list[ModelNodeGraphInfo] = Field(
        default_factory=list,
        description="List of node information for wiring",
    )
    instantiation_duration_ms: float | None = Field(
        default=None,
        ge=0,
        description="How long graph instantiation took in milliseconds",
    )

    @classmethod
    def create(
        cls,
        *,
        graph_id: UUID | None = None,
        node_count: int = 0,
        nodes: list[ModelNodeGraphInfo] | None = None,
        instantiation_duration_ms: float | None = None,
        correlation_id: UUID | None = None,
    ) -> "ModelNodeGraphReadyEvent":
        """Factory method for creating a node graph ready event."""
        return cls(
            graph_id=graph_id or uuid4(),
            node_count=node_count,
            nodes=nodes or [],
            instantiation_duration_ms=instantiation_duration_ms,
            correlation_id=correlation_id,
        )
