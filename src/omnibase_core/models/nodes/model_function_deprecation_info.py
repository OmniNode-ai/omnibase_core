"""
Function Deprecation Information Model.

Deprecation and lifecycle information for functions.
Part of the ModelFunctionNodeMetadata restructuring.
"""

from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_deprecation_status import EnumDeprecationStatus
from omnibase_core.models.metadata.model_semver import ModelSemVer


class TypedDictDeprecationSummary(TypedDict):
    """Type-safe dictionary for deprecation summary."""

    is_deprecated: bool
    has_replacement: bool
    deprecated_since: str | None
    replacement: str | None
    status: str  # EnumDeprecationStatus.value


class ModelFunctionDeprecationInfo(BaseModel):
    """
    Function deprecation and lifecycle information.

    Contains deprecation details:
    - Deprecation version and replacement info
    - Lifecycle status
    """

    # Deprecation information (2 fields, but minimal)
    deprecated_since: ModelSemVer | None = Field(
        default=None,
        description="Version when deprecated",
    )
    replacement: str | None = Field(
        default=None,
        description="Replacement function if deprecated",
    )

    def is_deprecated(self) -> bool:
        """Check if function is deprecated."""
        return self.deprecated_since is not None

    def has_replacement(self) -> bool:
        """Check if function has a replacement."""
        return self.replacement is not None

    def get_deprecation_status(self) -> EnumDeprecationStatus:
        """Get deprecation status as enum."""
        if not self.is_deprecated():
            return EnumDeprecationStatus.ACTIVE

        if self.has_replacement():
            return EnumDeprecationStatus.DEPRECATED_WITH_REPLACEMENT

        return EnumDeprecationStatus.DEPRECATED

    def get_deprecation_status_description(self) -> str:
        """Get deprecation status description as human-readable string."""
        if not self.is_deprecated():
            return "active"

        if self.has_replacement():
            return f"deprecated since {self.deprecated_since}, use {self.replacement}"

        return f"deprecated since {self.deprecated_since}"

    def get_deprecation_summary(self) -> TypedDictDeprecationSummary:
        """Get deprecation information summary."""
        return {
            "is_deprecated": self.is_deprecated(),
            "has_replacement": self.has_replacement(),
            "deprecated_since": (
                str(self.deprecated_since) if self.deprecated_since else None
            ),
            "replacement": self.replacement,
            "status": self.get_deprecation_status().value,
        }

    @classmethod
    def create_active(cls) -> ModelFunctionDeprecationInfo:
        """Create active (non-deprecated) function info."""
        return cls()

    @classmethod
    def create_deprecated(
        cls,
        deprecated_since: ModelSemVer,
        replacement: str | None = None,
    ) -> ModelFunctionDeprecationInfo:
        """Create deprecated function info."""
        return cls(
            deprecated_since=deprecated_since,
            replacement=replacement,
        )


# Export for use
__all__ = ["ModelFunctionDeprecationInfo", "TypedDictDeprecationSummary"]
