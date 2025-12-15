"""
Event model for node graph ready state.

Published when the node graph is fully instantiated,
triggering the event bus wiring process.
"""

from uuid import UUID, uuid4

from pydantic import Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError
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

    @model_validator(mode="after")
    def validate_node_count_consistency(self) -> "ModelNodeGraphReadyEvent":
        """Validate that node_count matches len(nodes) when both are provided."""
        # Only validate if nodes list is non-empty and node_count was explicitly set
        # This allows node_count=0 with empty nodes list (default case)
        if self.nodes and self.node_count != len(self.nodes):
            msg = (
                f"node_count ({self.node_count}) does not match "
                f"len(nodes) ({len(self.nodes)})"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return self

    @classmethod
    def create(
        cls,
        *,
        graph_id: UUID | None = None,
        node_count: int | None = None,
        nodes: list[ModelNodeGraphInfo] | None = None,
        instantiation_duration_ms: float | None = None,
        correlation_id: UUID | None = None,
    ) -> "ModelNodeGraphReadyEvent":
        """Factory method for creating a node graph ready event.

        Args:
            graph_id: Unique identifier for this node graph instance.
            node_count: Total number of nodes. If None and nodes is provided,
                derived from len(nodes).
            nodes: List of node information for wiring.
            instantiation_duration_ms: How long graph instantiation took.
            correlation_id: Correlation ID for request tracing.

        Returns:
            A new ModelNodeGraphReadyEvent instance.
        """
        nodes_list = nodes if nodes is not None else []
        # Derive node_count from nodes if not explicitly provided
        actual_node_count = node_count if node_count is not None else len(nodes_list)
        return cls(
            graph_id=graph_id or uuid4(),
            node_count=actual_node_count,
            nodes=nodes_list,
            instantiation_duration_ms=instantiation_duration_ms,
            correlation_id=correlation_id,
        )
