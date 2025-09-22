"""
Input state model for version parsing.

Type-safe input state container that replaces complex union types
with structured validation for version parsing operations.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .model_semver import ModelSemVer


class ModelInputState(BaseModel):
    """
    Type-safe input state container for version parsing.

    Replaces dict[str, str | int | ModelSemVer | dict[str, int]] with
    structured input state that handles version parsing requirements.
    """

    # Version field (required for parsing)
    version: ModelSemVer | dict[str, int] | None = Field(
        None,
        description="Version information as ModelSemVer or dict with major/minor/patch",
    )

    # Additional fields that might be present in input state
    additional_fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional fields in the input state",
    )

    @classmethod
    def from_dict(cls, input_dict: dict[str, Any]) -> ModelInputState:
        """Create input state from a dictionary."""
        version_data = input_dict.get("version")

        # Extract version and other fields
        additional_fields = {k: v for k, v in input_dict.items() if k != "version"}

        return cls(
            version=version_data,
            additional_fields=additional_fields,
        )

    def get_version_data(self) -> ModelSemVer | dict[str, int] | None:
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
__all__ = ["ModelInputState"]
