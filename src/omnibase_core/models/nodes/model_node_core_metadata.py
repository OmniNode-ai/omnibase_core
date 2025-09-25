"""
Node Core Metadata Model.

Essential node identification and basic information.
Part of the ModelNodeMetadataInfo restructuring.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.models.metadata.model_semver import ModelSemVer
from omnibase_core.utils.uuid_utilities import uuid_from_string


class ModelNodeCoreMetadata(BaseModel):
    """
    Core node metadata with essential identification.

    Contains only the most critical node information:
    - Identity (ID, name, type)
    - Status and health
    - Version information
    """

    # Core identification - UUID-based entity references
    node_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the node entity",
    )
    node_display_name: str = Field(default="", description="Human-readable node name")
    node_type: EnumMetadataNodeType = Field(..., description="Node type")

    # Status information (2 fields)
    status: EnumMetadataNodeStatus = Field(
        default=EnumMetadataNodeStatus.ACTIVE,
        description="Node status",
    )
    health: EnumNodeHealthStatus = Field(
        default=EnumNodeHealthStatus.HEALTHY,
        description="Node health",
    )

    # Version (1 field, but structured)
    version: ModelSemVer | None = Field(default=None, description="Node version")

    def is_active(self) -> bool:
        """Check if node is active."""
        return self.status == EnumMetadataNodeStatus.ACTIVE

    def is_healthy(self) -> bool:
        """Check if node is healthy."""
        return self.health == EnumNodeHealthStatus.HEALTHY

    def get_status_summary(self) -> dict[str, str]:
        """Get concise status summary."""
        return {
            "status": self.status.value,
            "health": self.health.value,
            "version": str(self.version) if self.version else "unknown",
        }

    @property
    def node_name(self) -> str:
        """Get node name with fallback to UUID-based name."""
        return self.node_display_name or f"node_{str(self.node_id)[:8]}"

    @node_name.setter
    def node_name(self, value: str) -> None:
        """Set node name."""
        self.node_display_name = value

    @classmethod
    def create_simple(
        cls,
        node_name: str,
        node_type: EnumMetadataNodeType = EnumMetadataNodeType.FUNCTION,
    ) -> ModelNodeCoreMetadata:
        """Create simple core metadata with deterministic UUID."""
        return cls(
            node_id=uuid_from_string(node_name, "node"),
            node_display_name=node_name,
            node_type=node_type,
        )


# Export for use
__all__ = ["ModelNodeCoreMetadata"]
