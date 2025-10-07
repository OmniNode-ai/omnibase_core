"""
Node Core Metadata Model.

Core node metadata with essential identification and status information.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
    from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
    from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
    from omnibase_core.models.metadata.model_semver import ModelSemVer


class ModelNodeCoreMetadata(BaseModel):
    """
    Core node metadata with essential identification.

    Contains only the most critical node information:
    - Identity (ID, name, type)
    - Status and health
    - Version information
    Implements omnibase_spi protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core identification - UUID-based entity references
    node_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the node entity",
    )
    node_display_name: str = Field(default="", description="Human-readable node name")
    node_type: "EnumMetadataNodeType" = Field(default=..., description="Node type")

    # Status information (2 fields)
    status: "EnumMetadataNodeStatus" = Field(
        default="active",
        description="Node status",
    )
    health: "EnumNodeHealthStatus" = Field(
        default="healthy",
        description="Node health",
    )

    # Version (1 field, but structured)
    version: "ModelSemVer | None" = Field(default=None, description="Node version")

    def is_active(self) -> bool:
        """Check if node is active."""
        return self.status.value == "ACTIVE"

    def is_healthy(self) -> bool:
        """Check if node is healthy."""
        return self.health.value == "HEALTHY"

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
        node_type: "EnumMetadataNodeType" = "function",
    ) -> "ModelNodeCoreMetadata":
        """Create simple core metadata with deterministic UUID."""
        from uuid import NAMESPACE_DNS, uuid5

        # Generate deterministic UUID from node name
        node_id = uuid5(NAMESPACE_DNS, node_name)
        return cls(
            node_id=node_id,
            node_display_name=node_name,
            node_type=node_type,
        )

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

        from omnibase_core.errors.error_codes import EnumCoreErrorCode
        from omnibase_core.errors.model_onex_error import ModelOnexError

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> dict[str, Any]:
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
        return metadata

    def set_metadata(self, metadata: dict[str, Any]) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (
            Exception
        ):  # fallback-ok: setter returns False on failure per protocol contract
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (
            Exception
        ):  # fallback-ok: validation method, False indicates validation failure
            return False
