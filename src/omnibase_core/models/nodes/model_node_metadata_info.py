"""
Node Metadata Info Model.

Simple model for node metadata information used in CLI output.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ...enums.enum_metadata_node_status import EnumMetadataNodeStatus
from ...protocols.protocol_node_info_like import NodeInfoLike
from ..metadata.model_semver import ModelSemVer


class ModelNodeMetadataInfo(BaseModel):
    """
    Node metadata information model.

    Used for capturing metadata about nodes in CLI output and processing.
    """

    # Core metadata
    node_id: UUID = Field(default_factory=uuid4, description="Node identifier")
    node_name: str = Field(..., description="Node name")
    node_type: str = Field(..., description="Node type")

    # Metadata details
    description: str | None = Field(default=None, description="Node description")
    version: ModelSemVer | None = Field(default=None, description="Node version")
    author: str | None = Field(default=None, description="Node author")

    # Status information
    status: EnumMetadataNodeStatus = Field(
        default=EnumMetadataNodeStatus.ACTIVE, description="Node status"
    )
    health: str = Field(default="healthy", description="Node health")

    # Timestamps
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp",
    )
    last_accessed: datetime | None = Field(
        default=None,
        description="Last access timestamp",
    )

    # Usage and performance
    usage_count: int = Field(default=0, description="Usage count", ge=0)
    error_count: int = Field(default=0, description="Error count", ge=0)
    success_rate: float = Field(
        default=100.0,
        description="Success rate percentage",
        ge=0.0,
        le=100.0,
    )

    # Configuration and capabilities
    capabilities: list[str] = Field(
        default_factory=list,
        description="Node capabilities",
    )
    tags: list[str] = Field(default_factory=list, description="Node tags")
    categories: list[str] = Field(default_factory=list, description="Node categories")

    # Dependencies
    dependencies: list[str] = Field(
        default_factory=list,
        description="Node dependencies",
    )
    dependents: list[str] = Field(
        default_factory=list,
        description="Nodes that depend on this",
    )

    # Custom metadata
    custom_metadata: dict[str, str | int | bool | float] = Field(
        default_factory=dict,
        description="Custom metadata fields",
    )

    def is_active(self) -> bool:
        """Check if node is active."""
        return self.status == EnumMetadataNodeStatus.ACTIVE

    def is_healthy(self) -> bool:
        """Check if node is healthy."""
        return self.health == "healthy"

    def has_errors(self) -> bool:
        """Check if node has errors."""
        return self.error_count > 0

    def get_success_rate(self) -> float:
        """Get success rate."""
        return self.success_rate

    def is_high_usage(self) -> bool:
        """Check if node has high usage (>100 uses)."""
        return self.usage_count > 100

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present."""
        if tag in self.tags:
            self.tags.remove(tag)

    def add_capability(self, capability: str) -> None:
        """Add a capability if not already present."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)

    def has_capability(self, capability: str) -> bool:
        """Check if node has a specific capability."""
        return capability in self.capabilities

    def add_category(self, category: str) -> None:
        """Add a category if not already present."""
        if category not in self.categories:
            self.categories.append(category)

    def increment_usage(self) -> None:
        """Increment usage count."""
        self.usage_count += 1

    def increment_errors(self) -> None:
        """Increment error count and update success rate."""
        self.error_count += 1
        if self.usage_count > 0:
            success_count = self.usage_count - self.error_count
            self.success_rate = (success_count / self.usage_count) * 100.0

    def update_accessed_time(self) -> None:
        """Update last accessed timestamp."""
        self.last_accessed = datetime.now(UTC)

    def get_summary(self) -> dict[str, str | int | bool | float | list[str] | None]:
        """Get node metadata summary."""
        return {
            "node_id": str(self.node_id),
            "node_name": self.node_name,
            "node_type": self.node_type,
            "status": self.status,
            "health": self.health,
            "version": str(self.version) if self.version else None,
            "usage_count": self.usage_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "capabilities": self.capabilities,
            "tags": self.tags,
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_errors": self.has_errors(),
        }

    @classmethod
    def create_simple(
        cls,
        node_id: UUID,
        node_name: str,
        node_type: str = "generic",
    ) -> "ModelNodeMetadataInfo":
        """Create a simple node metadata info."""
        return cls(
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
        )

    @classmethod
    def from_node_info(cls, node_info: NodeInfoLike) -> "ModelNodeMetadataInfo":
        """Create from node info object."""
        # Extract basic information
        return cls(
            node_id=getattr(node_info, "node_id", uuid4()),
            node_name=getattr(node_info, "node_name", "unknown"),
            node_type=getattr(node_info, "node_type", "generic"),
            description=getattr(node_info, "description", None),
            version=getattr(node_info, "version", None),
            status=getattr(node_info, "status", EnumMetadataNodeStatus.ACTIVE),
            health=getattr(node_info, "health", "healthy"),
        )


# Export for use
__all__ = ["ModelNodeMetadataInfo"]
