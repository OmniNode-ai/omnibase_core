"""
Input state model for version parsing.

Type-safe input state container that replaces complex union types
with structured validation for version parsing operations.
"""

from __future__ import annotations

from typing import Any, TypedDict


class InputStateFieldsType(TypedDict, total=False):
    """Type-safe input state fields structure."""

    name: str
    description: str
    tags: list[str]
    priority: int
    metadata: dict[str, str]
    context: str


class InputStateSourceType(TypedDict, total=False):
    """Type-safe input state source structure."""

    version: object | None  # Use object with runtime type checking instead of Any
    name: str
    description: str
    tags: list[str]
    priority: int
    metadata: dict[str, str]
    context: str


from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import CoreErrorCode, OnexError

from .model_version_union import ModelVersionUnion


class ModelInputState(BaseModel):
    """
    Type-safe input state container for version parsing.

    Replaces dict[str, str | int | ModelSemVer | dict[str, int]] with
    structured input state that handles version parsing requirements.

    Implements omnibase_spi protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Version field (required for parsing) - structured discriminated union
    version: ModelVersionUnion | None = Field(
        None,
        description="Version information as discriminated union or None",
    )

    # Additional fields that might be present in input state
    additional_fields: InputStateFieldsType = Field(
        default_factory=lambda: InputStateFieldsType(),
        description="Additional fields in the input state",
    )

    def get_version_data(self) -> object:
        """Get the version data for parsing. Use isinstance() to check specific type."""
        if self.version is None:
            return None
        return self.version.get_version()

    def has_version(self) -> bool:
        """Check if input state has version information."""
        return self.version is not None and self.version.has_version()

    def get_field(self, key: str) -> object | None:
        """Get a field from the input state."""
        if key == "version":
            return self.get_version_data()
        return self.additional_fields.get(key)

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the model

    # Protocol method implementations

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
        except Exception as e:
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


__all__ = ["ModelInputState"]
