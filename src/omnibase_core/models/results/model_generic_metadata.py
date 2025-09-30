"""
Generic metadata model to replace Dict[str, Any] usage for metadata fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.models.metadata.model_semver import ModelSemVer
from omnibase_core.models.types.model_onex_common_types import JsonSerializable


class ModelGenericMetadata(BaseModel):
    """
    Generic metadata container with flexible but typed fields.
    Replaces Dict[str, Any] for metadata fields across the codebase.
    """

    # Common metadata fields
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    created_by: str | None = Field(None, description="Creator identifier")
    updated_by: str | None = Field(None, description="Last updater identifier")
    version: ModelSemVer | None = Field(None, description="Version information")

    # Flexible fields for various use cases
    tags: list[str] | None = Field(
        default_factory=list,
        description="Associated tags",
    )
    labels: dict[str, str] | None = Field(
        default_factory=dict,
        description="Key-value labels",
    )
    annotations: dict[str, str] | None = Field(
        default_factory=dict,
        description="Key-value annotations",
    )

    # Additional flexible storage
    custom_fields: dict[str, JsonSerializable] | None = Field(
        default_factory=dict,
        description="Custom fields with basic types",
    )

    # For complex nested data (last resort)
    extended_data: dict[str, BaseModel] | None = Field(
        None,
        description="Extended data with nested models",
    )

    model_config = ConfigDict(
        extra="allow",
    )  # Allow additional fields for current standards

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return None
