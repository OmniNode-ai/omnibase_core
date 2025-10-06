from typing import Dict, Generic, Optional

from pydantic import Field

"""
Generic metadata model to replace Dict[str, Any] usage for metadata fields.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


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
    version: str | None = Field(default=None, description="Version information")

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
    custom_fields: dict[str, str | int | float | bool | list[str]] | None = Field(
        default_factory=dict,
        description="Custom fields with basic types",
    )

    # For complex nested data (last resort)
    extended_data: dict[str, BaseModel] | None = Field(
        default=None,
        description="Extended data with nested models",
    )

    model_config = ConfigDict(
        extra="allow",
    )  # Allow additional fields for current standards

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> Optional["ModelGenericMetadata"]:
        """Create from dict[str, Any]ionary for easy migration."""
        if data is None:
            return None
        return cls(**data)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value) -> None:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
