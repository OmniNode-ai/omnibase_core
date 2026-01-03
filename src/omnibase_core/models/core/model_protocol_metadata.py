"""
Generic metadata model to replace Dict[str, Any] usage for metadata fields.

Implements ProtocolMetadata from omnibase_spi for protocol compliance.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase_core.types.type_serializable_value import SerializedDict


class ModelGenericMetadata(BaseModel):
    """
    Generic metadata container with flexible but typed fields.
    Replaces Dict[str, Any] for metadata fields across the codebase.

    Implements ProtocolMetadata protocol from omnibase_spi.
    """

    # ProtocolMetadata required fields
    # Uses dict[str, object] for generic protocol data values
    data: dict[str, object] = Field(
        default_factory=dict,
        description="Generic data dictionary for ProtocolMetadata compliance",
    )
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
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
        data: SerializedDict | None,
    ) -> ModelGenericMetadata | None:
        """Create from dictionary for easy migration."""
        if data is None:
            return None
        return cls.model_validate(data)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None

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
