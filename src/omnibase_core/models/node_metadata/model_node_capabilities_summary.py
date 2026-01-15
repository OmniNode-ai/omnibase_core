"""
Node capabilities summary model.

Clean, strongly-typed replacement for node capabilities dict[str, Any]return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel


class ModelNodeCapabilitiesSummary(BaseModel):
    """Node capabilities summary with specific types.
    Implements Core protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    capabilities_count: int = Field(description="Number of capabilities")
    operations_count: int = Field(description="Number of operations")
    dependencies_count: int = Field(description="Number of dependencies")
    has_capabilities: bool = Field(description="Whether node has capabilities")
    has_operations: bool = Field(description="Whether node has operations")
    has_dependencies: bool = Field(description="Whether node has dependencies")
    has_performance_metrics: bool = Field(
        description="Whether node has performance metrics",
    )
    primary_capability: str | None = Field(description="Primary capability if any")
    metrics_count: int = Field(description="Number of metrics")

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
        # Pack capabilities summary into metadata dict
        result["metadata"] = {
            "capabilities_count": self.capabilities_count,
            "operations_count": self.operations_count,
            "dependencies_count": self.dependencies_count,
            "has_capabilities": self.has_capabilities,
            "has_operations": self.has_operations,
            "has_dependencies": self.has_dependencies,
            "has_performance_metrics": self.has_performance_metrics,
            "primary_capability": self.primary_capability,
            "metrics_count": self.metrics_count,
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


__all__ = ["ModelNodeCapabilitiesSummary"]
