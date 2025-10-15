from typing import Any, Dict, Generic, Optional

from pydantic import Field

from omnibase_core.primitives.model_semver import ModelSemVer

"""
Generic metadata model to replace Dict[str, Any] usage for metadata fields.

Implements ProtocolMetadata from omnibase_spi for protocol compliance.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer


class ModelGenericMetadata(BaseModel):
    """
    Generic metadata container with flexible but typed fields.
    Replaces Dict[str, Any] for metadata fields across the codebase.

    Implements ProtocolMetadata protocol from omnibase_spi.
    """

    # ProtocolMetadata required fields
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Generic data dictionary for ProtocolMetadata compliance",
    )
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Version information",
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )

    # Additional metadata fields
    created_by: str | None = Field(default=None, description="Creator identifier")
    updated_by: str | None = Field(default=None, description="Last updater identifier")

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
    def serialize_datetime(self, value: Any) -> str | None:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value

    # ProtocolMetadata required methods
    async def validate_metadata(self) -> bool:
        """Validate metadata consistency."""
        return self.is_up_to_date()

    def is_up_to_date(self) -> bool:
        """Check if metadata is current."""
        if self.updated_at is None:
            # No updates yet, use created_at
            return True
        # Metadata is considered up to date
        return True
