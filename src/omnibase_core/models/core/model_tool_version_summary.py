"""
Tool Version Summary Model.

Summary of tool version information.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelToolVersionSummary(BaseModel):
    """Summary of tool version information."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    version: str = Field(description="Semantic version string")
    status: str = Field(description="Version status value")
    is_active: bool = Field(description="Whether version is active")
    is_deprecated: bool = Field(description="Whether version is deprecated")
    is_end_of_life: bool = Field(description="Whether version is end of life")
    lifecycle_phase: str = Field(description="Current lifecycle phase")
    breaking_changes: bool = Field(description="Whether has breaking changes")
    recommended: bool = Field(description="Whether version is recommended")
    has_deprecation_date: bool = Field(description="Whether has deprecation date")
    has_end_of_life_date: bool = Field(description="Whether has end of life date")


__all__ = ["ModelToolVersionSummary"]
