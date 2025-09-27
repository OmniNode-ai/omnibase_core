"""
Example metadata summary model.

This module provides the ModelExampleMetadataSummary class for clean
metadata summary following ONEX naming conventions.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue
from omnibase_core.models.metadata.model_semver import ModelSemVer


class ModelExampleMetadataSummary(BaseModel):
    """Clean model for metadata summary."""

    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Update timestamp")
    version: ModelSemVer | None = Field(None, description="Metadata version")
    author_id: UUID | None = Field(None, description="UUID of the author")
    author_display_name: str | None = Field(
        None,
        description="Human-readable author name",
    )
    tags: list[str] = Field(default_factory=list, description="Associated tags")
    custom_fields: dict[str, ModelMetadataValue] = Field(
        default_factory=dict,
        description="Custom metadata fields with type-safe values",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export the model
__all__ = ["ModelExampleMetadataSummary"]
