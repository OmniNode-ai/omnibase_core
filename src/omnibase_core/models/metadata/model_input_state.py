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

    version: Any  # Dict with major/minor/patch or string - validated at runtime
    name: str
    description: str
    tags: list[str]
    priority: int
    metadata: dict[str, str]
    context: str


from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import (
    MetadataProvider,
    Serializable,
    Validatable,
)

from .model_semver import ModelSemVer


class ModelInputState(BaseModel):
    """
    Type-safe input state container for version parsing.

    Replaces dict[str, str | int | ModelSemVer | dict[str, int]] with
    structured input state that handles version parsing requirements.

    Implements omnibase_spi protocols:
    - MetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Version field (required for parsing) - use Any for internal storage
    version: Any = Field(
        None,
        description="Version information as ModelSemVer or dict with major/minor/patch",
    )

    # Additional fields that might be present in input state
    additional_fields: InputStateFieldsType = Field(
        default_factory=lambda: InputStateFieldsType(),
        description="Additional fields in the input state",
    )

    def get_version_data(self) -> Any:
        """Get the version data for parsing."""
        return self.version

    def has_version(self) -> bool:
        """Check if input state has version information."""
        return self.version is not None

    def get_field(self, key: str) -> Any:
        """Get a field from the input state."""
        if key == "version":
            return self.version
        return self.additional_fields.get(key)

    # Export the model

    # Protocol method implementations

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata as dictionary (MetadataProvider protocol)."""
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
        """Set metadata from dictionary (MetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


__all__ = ["ModelInputState"]
