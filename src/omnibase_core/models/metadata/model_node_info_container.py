"""
Node info container model.

Clean, strongly-typed Pydantic model for containing node information.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .model_node_info_summary import ModelNodeInfoSummary


class ModelNodeInfoContainer(BaseModel):
    """
    Clean, strongly-typed container for node information.

    Replaces: dict[str, ModelNodeInfoData] type alias
    With proper structured data using Pydantic validation.

    Note: Does NOT implement ProtocolMetadataProvider or ProtocolSerializable.
    Use Pydantic's native model_dump() for serialization.
    """

    nodes: dict[UUID, ModelNodeInfoSummary] = Field(
        default_factory=dict,
        description="Collection of node information by node ID",
    )

    def add_node(self, node_id: UUID, node_info: ModelNodeInfoSummary) -> None:
        """Add a node to the container."""
        self.nodes[node_id] = node_info

    def get_node(self, node_id: UUID) -> ModelNodeInfoSummary | None:
        """Get a node from the container."""
        return self.nodes.get(node_id)

    def remove_node(self, node_id: UUID) -> bool:
        """Remove a node from the container. Returns True if node was removed."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            return True
        return False

    def get_node_count(self) -> int:
        """Get the total number of nodes in the container."""
        return len(self.nodes)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


__all__ = ["ModelNodeInfoContainer"]
