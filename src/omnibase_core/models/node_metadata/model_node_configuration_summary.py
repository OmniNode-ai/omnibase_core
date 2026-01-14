"""
Node configuration summary model.

Clean, strongly-typed replacement for node configuration dict[str, Any]return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel


class ModelNodeConfigurationSummary(BaseModel):
    """Node configuration summary with strongly-typed values.
    Implements Core protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Execution config using typed metadata values
    execution: dict[str, ModelMetadataValue | None] = Field(
        description="Execution configuration summary with type-safe values",
    )

    # Resources using numeric values for consistency
    resources: dict[str, ModelNumericValue | None] = Field(
        description="Resource configuration summary with numeric values",
    )

    # Features simplified - use string list[Any]for feature flags
    features: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Feature configuration as string list[Any]s",
    )

    # Connection config using string values (most common for connection strings, hosts, etc.)
    connection: dict[str, str | None] = Field(
        description="Connection configuration summary (string values)",
    )
    is_production_ready: bool = Field(
        description="Whether configuration is production ready",
    )
    is_performance_optimized: bool = Field(
        description="Whether configuration is performance optimized",
    )
    has_custom_settings: bool = Field(
        description="Whether configuration has custom settings",
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
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Pack configuration summary into metadata dict
        result["metadata"] = {
            "is_production_ready": self.is_production_ready,
            "is_performance_optimized": self.is_performance_optimized,
            "has_custom_settings": self.has_custom_settings,
            "features_keys": list(self.features.keys()) if self.features else [],
            "connection_keys": list(self.connection.keys()) if self.connection else [],
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


# NOTE: model_rebuild() not needed - Pydantic v2 handles forward references automatically
# ModelMetadataValue is imported at runtime, Pydantic will resolve references lazily

__all__ = ["ModelNodeConfigurationSummary"]
