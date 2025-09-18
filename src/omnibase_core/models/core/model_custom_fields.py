"""
Custom Fields Model.

Type-safe custom fields container replacing Dict[str, Any]
with structured extension field management.
"""

from typing import Union

from pydantic import BaseModel, Field

# Define allowed custom field value types
CustomFieldValue = Union[str, int, bool, float, list[str], list[int]]


class ModelCustomFields(BaseModel):
    """
    Type-safe custom fields container.

    Provides structured custom field management replacing
    Dict[str, Any] with type-safe extension points.
    """

    fields: dict[str, CustomFieldValue] = Field(
        default_factory=dict,
        description="Custom field values",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Field metadata (descriptions, types, etc.)",
    )

    def get_string(self, key: str, default: str = "") -> str:
        """Get string field value."""
        value = self.fields.get(key, default)
        return str(value) if value is not None else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer field value."""
        value = self.fields.get(key, default)
        return int(value) if isinstance(value, int | float) else default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean field value."""
        value = self.fields.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return str(value).lower() in ("true", "yes", "1", "on")
        return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float field value."""
        value = self.fields.get(key, default)
        return float(value) if isinstance(value, int | float) else default

    def get_list(self, key: str, default: list[str] | None = None) -> list[str]:
        """Get list field value."""
        if default is None:
            default = []
        value = self.fields.get(key, default)
        if isinstance(value, list):
            return [str(item) for item in value]
        return default

    def set_field(
        self,
        key: str,
        value: CustomFieldValue,
        description: str | None = None,
    ) -> None:
        """Set custom field value."""
        self.fields[key] = value
        if description:
            self.metadata[key] = description

    def has_field(self, key: str) -> bool:
        """Check if custom field exists."""
        return key in self.fields

    def remove_field(self, key: str) -> None:
        """Remove custom field."""
        self.fields.pop(key, None)
        self.metadata.pop(key, None)

    def get_field_description(self, key: str) -> str | None:
        """Get description for a custom field."""
        return self.metadata.get(key)

    def get_all_keys(self) -> list[str]:
        """Get all custom field keys."""
        return list(self.fields.keys())

    def to_dict(self) -> dict[str, CustomFieldValue]:
        """Convert custom fields to dictionary."""
        return self.fields.copy()
