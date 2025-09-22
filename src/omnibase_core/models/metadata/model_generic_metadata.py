"""
Generic metadata model for flexible data storage.
"""

from __future__ import annotations

from typing import Generic, TypeVar, cast
from uuid import UUID

from omnibase_spi.protocols.types import ProtocolSupportedMetadataType
from pydantic import BaseModel, Field

from ..infrastructure.model_cli_value import ModelCliValue
from .model_semver import ModelSemVer

# Simple TypeVar constraint for metadata types
T = TypeVar("T", str, int, bool, float)


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
    custom_fields: dict[str, ModelCliValue] | None = Field(
        default=None,
        description="Custom metadata fields with strongly-typed values",
    )

    def get_field(self, key: str, default: T) -> T:
        """Get a custom field value with type safety."""
        if self.custom_fields is None:
            return default
        cli_value = self.custom_fields.get(key)
        if cli_value is None:
            return default
        return cast(T, cli_value.to_python_value())

    def set_field(self, key: str, value: T) -> None:
        """Set a custom field value with type validation."""
        if not isinstance(value, (str, int, bool, float)):
            raise TypeError(
                f"Value must be str, int, bool, or float, got {type(value)}",
            )
        if self.custom_fields is None:
            self.custom_fields = {}
        self.custom_fields[key] = ModelCliValue.from_any(value)

    def get_typed_field(self, key: str, field_type: type[T], default: T) -> T:
        """Get a custom field value with specific type checking."""
        if self.custom_fields is None:
            return default
        cli_value = self.custom_fields.get(key)
        if cli_value is None:
            return default
        python_value = cli_value.to_python_value()
        if isinstance(python_value, field_type):
            return python_value
        return default

    def set_typed_field(self, key: str, value: T) -> None:
        """Set a custom field value with runtime type validation."""
        if isinstance(value, ProtocolSupportedMetadataType):
            # Initialize custom_fields if needed
            if self.custom_fields is None:
                self.custom_fields = {}

            # Convert to ModelCliValue for strongly-typed storage
            if hasattr(value, "__dict__"):
                # For complex objects, store as string representation
                self.custom_fields[key] = ModelCliValue.from_string(str(value))
            # For primitive types, use ModelCliValue.from_any() for type-safe storage
            elif isinstance(value, (str, int, float, bool)):
                self.custom_fields[key] = ModelCliValue.from_any(value)
            else:
                self.custom_fields[key] = ModelCliValue.from_string(str(value))
        else:
            raise TypeError(
                f"Value type {type(value)} not supported for metadata storage",
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
