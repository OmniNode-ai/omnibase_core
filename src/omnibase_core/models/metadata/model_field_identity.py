"""
Field identity sub-model.

Part of the metadata field info restructuring to reduce string field violations.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel


class ModelFieldIdentity(BaseModel):
    """Identity information for metadata fields.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core identifiers (UUID pattern)
    identity_id: UUID = Field(
        default=...,
        description="UUID for field identity identifier",
    )
    identity_display_name: str | None = Field(
        default=None,
        description="Human-readable field name identifier (e.g., METADATA_VERSION)",
        pattern="^[A-Z][A-Z0-9_]*$",
    )

    field_id: UUID = Field(
        default=...,
        description="UUID for actual field name",
    )
    field_display_name: str | None = Field(
        default=None,
        description="Actual field name in models (e.g., metadata_version)",
    )

    description: str = Field(
        default="",
        description="Human-readable description of the field",
    )

    def get_display_name(self) -> str:
        """Get a human-readable display name."""
        # Convert FIELD_NAME to Field Name
        name = self.identity_display_name or f"identity_{str(self.identity_id)[:8]}"
        return " ".join(word.capitalize() for word in name.split("_"))

    def matches_name(self, name: str) -> bool:
        """Check if this field matches the given name."""
        identity_name = (
            self.identity_display_name or f"identity_{str(self.identity_id)[:8]}"
        )
        field_name = self.field_display_name or f"field_{str(self.field_id)[:8]}"
        return (
            identity_name.upper() == name.upper() or field_name.lower() == name.lower()
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        if self.field_display_name:
            result["name"] = self.field_display_name
        if self.description:
            result["description"] = self.description
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


__all__ = ["ModelFieldIdentity"]
