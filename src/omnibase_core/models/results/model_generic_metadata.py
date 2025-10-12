from __future__ import annotations

import json
from typing import Dict, Generic

from pydantic import Field

from omnibase_core.primitives.model_semver import ModelSemVer

"""
Generic metadata model to replace Dict[str, Any] usage for metadata fields.
"""


from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.primitives.model_semver import ModelSemVer


class ModelGenericMetadata(BaseModel):
    """
    Generic metadata container with flexible but typed fields.
    Replaces Dict[str, Any] for metadata fields across the codebase.
    """

    # Common metadata fields
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )
    created_by: str | None = Field(default=None, description="Creator identifier")
    updated_by: str | None = Field(default=None, description="Last updater identifier")
    version: ModelSemVer | None = Field(default=None, description="Version information")

    # Flexible fields for various use cases
    tags: list[str] = Field(
        default_factory=list,
        description="Associated tags",
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Key-value labels",
    )
    annotations: Dict[str, str] = Field(
        default_factory=dict,
        description="Key-value annotations",
    )

    # Additional flexible storage (non-recursive for Pydantic compatibility)
    # BOUNDARY_LAYER_EXCEPTION: Uses Any for flexible metadata storage
    # Supporting various JSON-serializable types validated at runtime
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom fields with JSON-serializable types",
    )

    # For complex nested data - use JSON string representation
    extended_data_json: str | None = Field(
        default=None,
        description="Extended data as JSON string (for nested structures)",
    )

    model_config = ConfigDict(
        extra="allow",
    )  # Allow additional fields for current standards

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelGenericMetadata":
        """Create instance from dictionary."""
        if not isinstance(data, dict):
            data = {}
        return cls.model_validate(data)
