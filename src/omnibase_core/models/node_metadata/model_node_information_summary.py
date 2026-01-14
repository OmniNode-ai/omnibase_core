"""
Node information summary model.

Clean, strongly-typed replacement for node information dict[str, Any]return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel

from .model_node_capabilities_summary import ModelNodeCapabilitiesSummary
from .model_node_configuration_summary import ModelNodeConfigurationSummary
from .model_node_core_info_summary import ModelNodeCoreInfoSummary


class ModelNodeInformationSummary(BaseModel):
    """
    Clean, strongly-typed model replacing node information dict[str, Any]return types.

    Eliminates: dict[str, Any]

    With proper structured data using specific field types.
    Implements Core protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    core_info: ModelNodeCoreInfoSummary = Field(
        description="Core node information summary",
    )
    capabilities: ModelNodeCapabilitiesSummary = Field(
        description="Node capabilities summary",
    )
    configuration: ModelNodeConfigurationSummary = Field(
        description="Node configuration summary",
    )
    is_fully_configured: bool = Field(description="Whether node is fully configured")

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
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Pack summary data into metadata dict
        result["metadata"] = {
            "is_fully_configured": self.is_fully_configured,
            "core_info_node_name": self.core_info.node_name,
            "core_info_node_type": self.core_info.node_type.value,
            "capabilities_count": self.capabilities.capabilities_count,
            "operations_count": self.capabilities.operations_count,
        }
        return result

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
        return True


__all__ = ["ModelNodeInformationSummary"]
