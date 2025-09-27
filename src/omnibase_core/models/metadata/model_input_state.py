"""
Input state model for version parsing.

Type-safe input state container that replaces complex union types
with structured validation for version parsing operations.
"""

from __future__ import annotations

from typing import TypedDict


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

    version: object  # Dict with major/minor/patch or string - validated at runtime
    name: str
    description: str
    tags: list[str]
    priority: int
    metadata: dict[str, str]
    context: str


from pydantic import BaseModel, Field

from .model_semver import ModelSemVer


class ModelInputState(BaseModel):
    """
    Type-safe input state container for version parsing.

    Replaces dict[str, str | int | ModelSemVer | dict[str, int]] with
    structured input state that handles version parsing requirements.
    """

    # Version field (required for parsing) - use object for internal storage
    version: object = Field(
        None,
        description="Version information as ModelSemVer or dict with major/minor/patch",
    )

    # Additional fields that might be present in input state
    additional_fields: InputStateFieldsType = Field(
        default_factory=lambda: InputStateFieldsType(),
        description="Additional fields in the input state",
    )

    def get_version_data(self) -> object:
        """Get the version data for parsing."""
        return self.version

    def has_version(self) -> bool:
        """Check if input state has version information."""
        return self.version is not None

    def get_field(self, key: str) -> object:
        """Get a field from the input state."""
        if key == "version":
            return self.version
        return self.additional_fields.get(key)

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export the model
__all__ = ["ModelInputState"]
