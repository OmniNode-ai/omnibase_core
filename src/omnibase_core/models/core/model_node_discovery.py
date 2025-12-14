from datetime import UTC, datetime

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_discovery_source import EnumDiscoverySource

from .model_discovery_metadata import ModelDiscoveryMetadata
from .model_node_reference import ModelNodeReference


class ModelNodeDiscovery(BaseModel):
    """Node discovery results from dynamic registry queries."""

    discovered_nodes: list[ModelNodeReference] = Field(
        default=...,
        description="List of discovered nodes",
    )
    discovery_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When discovery occurred",
    )
    discovery_source: EnumDiscoverySource = Field(
        default=...,
        description="Source of discovery",
    )
    total_nodes: int = Field(default=..., description="Total nodes discovered", ge=0)
    active_nodes: int = Field(default=..., description="Number of active nodes", ge=0)
    discovery_metadata: ModelDiscoveryMetadata | None = Field(
        default=None,
        description="Additional discovery metadata",
    )

    def get_node_by_name(self, node_name: str) -> ModelNodeReference | None:
        """Get a node by its name."""
        for node in self.discovered_nodes:
            if node.node_name == node_name:
                return node
        return None

    def get_nodes_by_type(self, node_type: str) -> list[ModelNodeReference]:
        """Get all nodes of a specific type."""
        return [
            node
            for node in self.discovered_nodes
            if hasattr(node, "node_type") and node.node_type == node_type
        ]

    def is_node_available(self, node_name: str) -> bool:
        """Check if a node is available in discovery results."""
        return self.get_node_by_name(node_name) is not None
