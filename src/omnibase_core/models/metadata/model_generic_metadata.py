"""
Generic metadata model for flexible data storage.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# Type variable for generic metadata
T = TypeVar("T")


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
    version: str | None = Field(
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

    def get_field(self, key: str, default: Any = None) -> Any:
        """Get a custom field value."""
        if self.custom_fields is None:
            return default
        return self.custom_fields.get(key, default)

    def set_field(self, key: str, value: Any) -> None:
        """Set a custom field value."""
        if self.custom_fields is None:
            self.custom_fields = {}
        self.custom_fields[key] = value

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
