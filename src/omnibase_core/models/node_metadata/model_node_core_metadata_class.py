"""
Node Core Metadata Model.

Core node metadata with essential identification and status information.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel

if TYPE_CHECKING:
    from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelNodeCoreMetadata(BaseModel):
    """
    Core node metadata with essential identification.

    Contains only the most critical node information:
    - Identity (ID, name, type)
    - Status and health
    - Version information
    Implements Core protocols:
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
    node_type: EnumMetadataNodeType = Field(default=..., description="Node type")

    # Status information (2 fields)
    status: EnumMetadataNodeStatus = Field(
        default=EnumMetadataNodeStatus.ACTIVE,
        description="Node status",
    )
    health: EnumHealthStatus = Field(
        default=EnumHealthStatus.HEALTHY,
        description="Node health",
    )

    # Version (1 field, but structured)
    version: "ModelSemVer | None" = Field(default=None, description="Node version")

    def is_active(self) -> bool:
        """Check if node is active."""
        return self.status == EnumMetadataNodeStatus.ACTIVE

    def is_healthy(self) -> bool:
        """Check if node is healthy."""
        return self.health == EnumHealthStatus.HEALTHY

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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

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

        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Map actual fields to TypedDictMetadataDict structure
        # node_name property always returns non-empty (has UUID fallback)
        result["name"] = self.node_name
        if self.version:
            result["version"] = self.version
        # Pack additional fields into metadata
        result["metadata"] = {
            "node_id": str(self.node_id),
            "node_type": self.node_type.value,
            "status": self.status.value,
            "health": self.health.value,
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
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

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True
