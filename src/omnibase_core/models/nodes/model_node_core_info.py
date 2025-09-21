"""
Node Core Information Model.

Core identification and metadata for nodes.
Part of the ModelNodeInformation restructuring.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_metadata_node_status import EnumMetadataNodeStatus
from ...enums.enum_metadata_node_type import EnumMetadataNodeType
from ...enums.enum_registry_status import EnumRegistryStatus
from ..metadata.model_semver import ModelSemVer


class ModelNodeCoreInfo(BaseModel):
    """
    Core node identification and metadata.

    Contains core node information:
    - Identity (ID, name, type, version)
    - Core metadata (description, author)
    - Status information
    - Timestamps
    """

    # Node identification (4 fields)
    node_id: UUID = Field(
        default_factory=uuid.uuid4,
        description="Node identifier",
    )
    node_display_name: str | None = Field(None, description="Human-readable node name")
    node_type: EnumMetadataNodeType = Field(..., description="Node type")
    node_version: ModelSemVer = Field(..., description="Node version")

    # Basic metadata (3 fields)
    description: str | None = Field(None, description="Node description")
    author_id: UUID | None = Field(None, description="UUID for node author")
    author_display_name: str | None = Field(
        None, description="Human-readable node author"
    )

    # Status information (2 fields)
    status: EnumMetadataNodeStatus = Field(
        default=EnumMetadataNodeStatus.ACTIVE,
        description="Node status",
    )
    health: EnumRegistryStatus = Field(
        default=EnumRegistryStatus.HEALTHY,
        description="Node health",
    )

    # Timestamps (2 fields)
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    def is_active(self) -> bool:
        """Check if node is active."""
        return self.status == EnumMetadataNodeStatus.ACTIVE

    def is_healthy(self) -> bool:
        """Check if node is healthy."""
        return self.health == EnumRegistryStatus.HEALTHY

    def has_description(self) -> bool:
        """Check if node has a description."""
        return bool(self.description)

    def has_author(self) -> bool:
        """Check if node has an author."""
        return bool(self.author)

    def get_core_summary(self) -> dict[str, str | bool | None]:
        """Get core node information summary."""
        return {
            "node_id": str(self.node_id),
            "node_name": self.node_name,
            "node_type": self.node_type.value,
            "node_version": str(self.node_version),
            "status": self.status.value,
            "health": self.health.value,
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_description": self.has_description(),
            "has_author": self.has_author(),
        }

    @classmethod
    def create_streamlined(
        cls,
        node_name: str,
        node_type: EnumMetadataNodeType,
        node_version: ModelSemVer,
        description: str | None = None,
    ) -> ModelNodeCoreInfo:
        """Create streamlined node core info."""
        return cls(
            node_display_name=node_name,
            node_type=node_type,
            node_version=node_version,
            description=description,
            author_id=None,
            author_display_name=None,
            created_at=None,
            updated_at=None,
        )

    @property
    def node_name(self) -> str:
        """Get node name."""
        return self.node_display_name or f"node_{str(self.node_id)[:8]}"

    @property
    def author(self) -> str | None:
        """Get author name."""
        return self.author_display_name


# Export for use
__all__ = ["ModelNodeCoreInfo"]
