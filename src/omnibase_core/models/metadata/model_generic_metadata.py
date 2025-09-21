"""
Generic metadata model for flexible data storage.
"""

from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

from .model_semver import ModelSemVer
from .protocols.protocol_supported_metadata_type import ProtocolSupportedMetadataType

# Simple TypeVar constraint for metadata types
T = TypeVar("T", str, int, bool, float)
# Union type for metadata value types
MetadataValueType = str | int | float | bool


class ModelGenericMetadata(BaseModel, Generic[T]):
    """Generic metadata storage with flexible fields."""

    metadata_id: UUID | None = Field(
        default=None,
        description="UUID for metadata identifier",
    )
    metadata_display_name: str | None = Field(
        default=None,
        description="Human-readable metadata name",
    )
    description: str | None = Field(
        default=None,
        description="Metadata description",
    )
    version: ModelSemVer | None = Field(
        default=None,
        description="Metadata version",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Metadata tags",
    )
    custom_fields: dict[str, MetadataValueType] | None = Field(
        default=None,
        description="Custom metadata fields",
    )

    def get_field(self, key: str, default: MetadataValueType) -> MetadataValueType:
        """Get a custom field value with type safety."""
        if self.custom_fields is None:
            return default
        return self.custom_fields.get(key, default)

    def set_field(self, key: str, value: MetadataValueType) -> None:
        """Set a custom field value with type validation."""
        if not isinstance(value, (str, int, bool, float)):
            raise TypeError(
                f"Value must be str, int, bool, or float, got {type(value)}"
            )
        if self.custom_fields is None:
            self.custom_fields = {}
        self.custom_fields[key] = value

    def get_typed_field(self, key: str, field_type: type[T], default: T) -> T:
        """Get a custom field value with specific type checking."""
        if self.custom_fields is None:
            return default
        value = self.custom_fields.get(key)
        if value is not None and isinstance(value, field_type):
            return value
        return default

    def set_typed_field(self, key: str, value: T) -> None:
        """Set a custom field value with runtime type validation."""
        if isinstance(value, ProtocolSupportedMetadataType):
            # Initialize custom_fields if needed
            if self.custom_fields is None:
                self.custom_fields = {}

            # Convert to a supported primitive type
            if hasattr(value, "__dict__"):
                # For complex objects, store as string representation
                self.custom_fields[key] = str(value)
            else:
                # For primitive types, store directly if they match MetadataValueType
                if isinstance(value, (str, int, float, bool)):
                    # Safe assignment since value is guaranteed to be one of the union types
                    self.custom_fields[key] = value
                else:
                    self.custom_fields[key] = str(value)
        else:
            raise TypeError(
                f"Value type {type(value)} not supported for metadata storage"
            )

    def has_field(self, key: str) -> bool:
        """Check if a custom field exists."""
        if self.custom_fields is None:
            return False
        return key in self.custom_fields

    def remove_field(self, key: str) -> bool:
        """Remove a custom field. Returns True if removed, False if not found."""
        if self.custom_fields is None:
            return False
        if key in self.custom_fields:
            del self.custom_fields[key]
            return True
        return False
