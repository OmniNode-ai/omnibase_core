"""
Tool Version Model.

Version information for a tool with lifecycle management.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

# Re-export from split module
from omnibase_core.models.core.model_tool_version_summary import ModelToolVersionSummary
from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase_core.enums.enum_tool_manifest import EnumVersionStatus


class ModelToolVersion(BaseModel):
    """Version information for a tool."""

    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Semantic version identifier",
    )
    status: "EnumVersionStatus" = Field(description="Version lifecycle status")
    release_date: str = Field(description="Version release date")
    breaking_changes: bool = Field(
        description="Whether version contains breaking changes",
    )
    recommended: bool = Field(description="Whether version is recommended for use")
    deprecation_date: str | None = Field(
        default=None,
        description="Date when version was deprecated",
    )
    end_of_life_date: str | None = Field(
        default=None,
        description="Date when version reaches end of life",
    )
    changelog: str | None = Field(
        default=None,
        description="Version changelog summary",
    )

    def is_active(self) -> bool:
        """Check if version is active."""
        return bool(self.status.value == "active")

    def is_deprecated(self) -> bool:
        """Check if version is deprecated."""
        return bool(self.status.value == "deprecated")

    def is_end_of_life(self) -> bool:
        """Check if version is end of life."""
        return bool(self.status.value == "end_of_life")

    def get_lifecycle_phase(self) -> str:
        """Get current lifecycle phase."""
        if self.is_end_of_life():
            return "end_of_life"
        elif self.is_deprecated():
            return "deprecated"
        elif self.status.value in ["alpha", "beta"]:
            return "development"
        else:
            return "active"

    def get_summary(self) -> ModelToolVersionSummary:
        """Get version summary."""
        return ModelToolVersionSummary(
            version=str(self.version),
            status=self.status.value,
            is_active=self.is_active(),
            is_deprecated=self.is_deprecated(),
            is_end_of_life=self.is_end_of_life(),
            lifecycle_phase=self.get_lifecycle_phase(),
            breaking_changes=self.breaking_changes,
            recommended=self.recommended,
            has_deprecation_date=self.deprecation_date is not None,
            has_end_of_life_date=self.end_of_life_date is not None,
        )


__all__ = [
    "ModelToolVersion",
    "ModelToolVersionSummary",  # Re-export from split module
]
