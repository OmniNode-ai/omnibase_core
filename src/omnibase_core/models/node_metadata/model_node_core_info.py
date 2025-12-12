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

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.enums.enum_registry_status import EnumRegistryStatus
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.typed_dict_core_summary import TypedDictCoreSummary


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
    node_display_name: str | None = Field(
        default=None, description="Human-readable node name"
    )
    node_type: EnumMetadataNodeType = Field(default=..., description="Node type")
    node_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Node version",
    )

    # Basic metadata (3 fields)
    description: str | None = Field(default=None, description="Node description")
    author_id: UUID | None = Field(default=None, description="UUID for node author")
    author_display_name: str | None = Field(
        default=None,
        description="Human-readable node author",
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
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )

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
        """Check if node has any author identifier or display name."""
        return bool(self.author_id or self.author_display_name)

    def get_core_summary(self) -> TypedDictCoreSummary:
        """Get core node information summary."""
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_type": self.node_type.value,
            "node_version": self.node_version,
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata  # type: ignore[return-value]

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


__all__ = ["ModelNodeCoreInfo"]
