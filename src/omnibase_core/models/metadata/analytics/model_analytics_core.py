"""
Analytics Core Model.

Core collection information and basic node counts for analytics.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.utils.uuid_utilities import uuid_from_string


class ModelAnalyticsCore(BaseModel):
    """
    Core analytics information with collection details and basic counts.

    Focused on fundamental collection identification and node counts.
    """

    # Core collection info - UUID-based entity references
    collection_id: UUID = Field(
        default_factory=lambda: uuid_from_string("default", "collection"),
        description="Unique identifier for the collection",
    )
    collection_display_name: str | None = Field(
        None,
        description="Human-readable collection name",
    )

    # Node counts
    total_nodes: int = Field(default=0, description="Total number of nodes")
    active_nodes: int = Field(default=0, description="Number of active nodes")
    deprecated_nodes: int = Field(default=0, description="Number of deprecated nodes")
    disabled_nodes: int = Field(default=0, description="Number of disabled nodes")

    @property
    def collection_name(self) -> str | None:
        """Get collection name with fallback."""
        return self.collection_display_name

    @property
    def active_node_ratio(self) -> float:
        """Get ratio of active nodes to total nodes."""
        if self.total_nodes == 0:
            return 0.0
        return self.active_nodes / self.total_nodes

    @property
    def deprecated_node_ratio(self) -> float:
        """Get ratio of deprecated nodes to total nodes."""
        if self.total_nodes == 0:
            return 0.0
        return self.deprecated_nodes / self.total_nodes

    @property
    def disabled_node_ratio(self) -> float:
        """Get ratio of disabled nodes to total nodes."""
        if self.total_nodes == 0:
            return 0.0
        return self.disabled_nodes / self.total_nodes

    def has_nodes(self) -> bool:
        """Check if collection has any nodes."""
        return self.total_nodes > 0

    def has_active_nodes(self) -> bool:
        """Check if collection has active nodes."""
        return self.active_nodes > 0

    def has_issues(self) -> bool:
        """Check if collection has deprecated or disabled nodes."""
        return self.deprecated_nodes > 0 or self.disabled_nodes > 0

    def update_node_counts(
        self,
        total: int,
        active: int,
        deprecated: int,
        disabled: int,
    ) -> None:
        """Update all node counts."""
        self.total_nodes = max(0, total)
        self.active_nodes = max(0, active)
        self.deprecated_nodes = max(0, deprecated)
        self.disabled_nodes = max(0, disabled)

    def add_nodes(
        self,
        total: int = 0,
        active: int = 0,
        deprecated: int = 0,
        disabled: int = 0,
    ) -> None:
        """Add to existing node counts."""
        self.total_nodes += max(0, total)
        self.active_nodes += max(0, active)
        self.deprecated_nodes += max(0, deprecated)
        self.disabled_nodes += max(0, disabled)

    @classmethod
    def create_for_collection(
        cls,
        collection_id: UUID,
        collection_name: str,
    ) -> ModelAnalyticsCore:
        """Create analytics core for specific collection."""
        return cls(
            collection_id=collection_id,
            collection_display_name=collection_name,
        )

    @classmethod
    def create_with_counts(
        cls,
        collection_name: str,
        total_nodes: int,
        active_nodes: int,
        deprecated_nodes: int = 0,
        disabled_nodes: int = 0,
    ) -> ModelAnalyticsCore:
        """Create analytics core with initial node counts."""
        return cls(
            collection_id=uuid_from_string(collection_name, "collection"),
            collection_display_name=collection_name,
            total_nodes=total_nodes,
            active_nodes=active_nodes,
            deprecated_nodes=deprecated_nodes,
            disabled_nodes=disabled_nodes,
        )


# Export for use
__all__ = ["ModelAnalyticsCore"]
