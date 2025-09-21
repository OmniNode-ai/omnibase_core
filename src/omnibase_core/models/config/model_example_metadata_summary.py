"""
Example metadata summary model.

This module provides the ModelExampleMetadataSummary class for clean
metadata summary following ONEX naming conventions.
"""

from pydantic import BaseModel, Field

from ..metadata.model_semver import ModelSemVer


class ModelExampleMetadataSummary(BaseModel):
    """Clean model for metadata summary."""

    created_at: str | None = Field(None, description="Creation timestamp")
    updated_at: str | None = Field(None, description="Update timestamp")
    version: ModelSemVer | None = Field(None, description="Metadata version")
    author: str | None = Field(None, description="Author information")
    tags: list[str] = Field(default_factory=list, description="Associated tags")
    custom_fields: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Custom metadata fields with basic types only"
    )
