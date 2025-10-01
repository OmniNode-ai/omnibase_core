"""
Node Core Metadata Model.

Essential node identification and basic information.
Part of the ModelNodeMetadataInfo restructuring.

Demonstrates ONEX discriminated union patterns for type-safe modeling.
"""

from __future__ import annotations

from typing import Any, Literal, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Discriminator, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.metadata.model_semver import ModelSemVer
from omnibase_core.utils.uuid_utilities import uuid_from_string


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
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
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
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
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
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


# ONEX Discriminated Union Pattern Example
# This demonstrates the ONEX standard for discriminated unions


class ModelNodeStatusActive(BaseModel):
    """Active node status with uptime tracking."""

    status_type: Literal["active"] = Field(
        default="active",
        description="Status discriminator",
    )
    uptime_seconds: int = Field(ge=0, description="Node uptime in seconds")
    last_heartbeat: str = Field(description="ISO timestamp of last heartbeat")


class ModelNodeStatusMaintenance(BaseModel):
    """Maintenance node status with estimated completion."""

    status_type: Literal["maintenance"] = Field(
        default="maintenance",
        description="Status discriminator",
    )
    estimated_completion: str = Field(
        description="ISO timestamp of estimated completion",
    )
    maintenance_reason: str = Field(description="Reason for maintenance")


class ModelNodeStatusError(BaseModel):
    """Error node status with error details."""

    status_type: Literal["error"] = Field(
        default="error",
        description="Status discriminator",
    )
    error_code: str = Field(description="Error classification code")
    error_message: str = Field(description="Human-readable error description")
    recovery_suggestion: str | None = Field(
        None,
        description="Suggested recovery action",
    )


def get_node_status_discriminator(v: Any) -> str:
    """Extract discriminator value for node status union."""
    if isinstance(v, dict):
        status_type = v.get("status_type", "active")
        return str(status_type)  # Ensure string type
    return str(getattr(v, "status_type", "active"))  # Ensure string type


# ONEX Discriminated Union Type
NodeStatusUnion = Union[
    ModelNodeStatusActive,
    ModelNodeStatusMaintenance,
    ModelNodeStatusError,
]

# Type alias with discriminator for Pydantic validation
NodeStatusDiscriminator = Discriminator(
    get_node_status_discriminator,
    custom_error_type="node_status_discriminator",
    custom_error_message="Invalid node status type",
    custom_error_context={"discriminator": "status_type"},
)

# Export for use
__all__ = [
    "ModelNodeCoreMetadata",
    "ModelNodeStatusActive",
    "ModelNodeStatusError",
    "ModelNodeStatusMaintenance",
    "NodeStatusDiscriminator",
    "NodeStatusUnion",
]
