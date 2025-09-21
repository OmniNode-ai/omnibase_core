"""
Generic metadata model for flexible data storage.
"""

from typing import Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, Field

from .model_semver import ModelSemVer

# Simple TypeVar constraint for metadata types
T = TypeVar("T", str, int, bool, float)


@runtime_checkable
class ModelProtocolSupportedMetadataType(Protocol):
    """Protocol for types that can be stored in metadata."""

    def __str__(self) -> str:
        """Must be convertible to string."""
        ...


class ModelGenericMetadata(BaseModel, Generic[T]):
    """Generic metadata storage with flexible fields."""

    name: str | None = Field(
        default=None,
        description="Metadata name or identifier",
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
    custom_fields: dict[str, str | int | bool | float] | None = Field(
        default=None,
        description="Custom metadata fields",
    )

    def get_field(
        self, key: str, default: str | int | bool | float | None = None
    ) -> str | int | bool | float | None:
        """Get a custom field value with type safety."""
        if self.custom_fields is None:
            return default
        return self.custom_fields.get(key, default)

    def set_field(self, key: str, value: str | int | bool | float) -> None:
        """Set a custom field value with type validation."""
        if not isinstance(value, (str, int, bool, float)):
            raise TypeError(
                f"Value must be str, int, bool, or float, got {type(value)}"
            )
        if self.custom_fields is None:
            self.custom_fields = {}
        self.custom_fields[key] = value

    def get_typed_field(
        self, key: str, field_type: type[T], default: T | None = None
    ) -> T | None:
        """Get a custom field value with specific type checking."""
        value = self.get_field(key)
        if value is not None and isinstance(value, field_type):
            return value
        return default

    def set_typed_field(self, key: str, value: T) -> None:
        """Set a custom field value with runtime type validation."""
        if isinstance(value, ModelProtocolSupportedMetadataType):
            # Convert to a supported primitive type
            if hasattr(value, "__dict__"):
                # For complex objects, store as string representation
                self.set_field(key, str(value))
            else:
                self.set_field(key, value)
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
