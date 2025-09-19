"""
Custom Fields Model.

Flexible storage for custom fields with type validation
and safe value retrieval for extensible models.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelCustomFields(BaseModel):
    """
    Custom fields storage with type validation.

    Provides safe storage and retrieval of custom fields
    with proper type validation and conversion methods.
    """

    # String fields
    string_fields: dict[str, str] = Field(
        default_factory=dict,
        description="String custom fields",
    )

    # Numeric fields
    int_fields: dict[str, int] = Field(
        default_factory=dict,
        description="Integer custom fields",
    )
    float_fields: dict[str, float] = Field(
        default_factory=dict,
        description="Float custom fields",
    )

    # Boolean fields
    bool_fields: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean custom fields",
    )

    # List fields (store as JSON strings for simplicity)
    list_fields: dict[str, list[Any]] = Field(
        default_factory=dict,
        description="List custom fields",
    )

    def set_field(self, name: str, value: Any) -> None:
        """Set a custom field with type validation."""
        if isinstance(value, str):
            self.string_fields[name] = value
        elif isinstance(value, int) and not isinstance(value, bool):
            self.int_fields[name] = value
        elif isinstance(value, float):
            self.float_fields[name] = value
        elif isinstance(value, bool):
            self.bool_fields[name] = value
        elif isinstance(value, list):
            self.list_fields[name] = value
        else:
            # Convert to string as fallback
            self.string_fields[name] = str(value)

    def get_field(self, name: str, default: Any = None) -> Any:
        """Get a custom field value."""
        # Check all field types
        if name in self.string_fields:
            return self.string_fields[name]
        if name in self.int_fields:
            return self.int_fields[name]
        if name in self.float_fields:
            return self.float_fields[name]
        if name in self.bool_fields:
            return self.bool_fields[name]
        if name in self.list_fields:
            return self.list_fields[name]
        return default

    def get_string(self, name: str, default: str = "") -> str:
        """Get a string field value."""
        if name in self.string_fields:
            return self.string_fields[name]
        # Try to convert from other types
        value = self.get_field(name)
        if value is not None:
            return str(value)
        return default

    def get_int(self, name: str, default: int = 0) -> int:
        """Get an integer field value."""
        if name in self.int_fields:
            return self.int_fields[name]
        # Try to convert from string
        if name in self.string_fields:
            try:
                return int(self.string_fields[name])
            except ValueError:
                pass
        return default

    def get_float(self, name: str, default: float = 0.0) -> float:
        """Get a float field value."""
        if name in self.float_fields:
            return self.float_fields[name]
        # Try to convert from string or int
        if name in self.string_fields:
            try:
                return float(self.string_fields[name])
            except ValueError:
                pass
        elif name in self.int_fields:
            return float(self.int_fields[name])
        return default

    def get_bool(self, name: str, *, default: bool = False) -> bool:
        """Get a boolean field value."""
        if name in self.bool_fields:
            return self.bool_fields[name]
        # Try to convert from string
        if name in self.string_fields:
            value = self.string_fields[name].lower()
            if value in ["true", "1", "yes", "on"]:
                return True
            if value in ["false", "0", "no", "off"]:
                return False
        return default

    def get_list(self, name: str, default: list[Any] | None = None) -> list[Any]:
        """Get a list field value."""
        if name in self.list_fields:
            return self.list_fields[name]
        return default or []

    def has_field(self, name: str) -> bool:
        """Check if a field exists."""
        return (
            name in self.string_fields
            or name in self.int_fields
            or name in self.float_fields
            or name in self.bool_fields
            or name in self.list_fields
        )

    def remove_field(self, name: str) -> bool:
        """Remove a field. Returns True if removed, False if not found."""
        removed = False
        if name in self.string_fields:
            del self.string_fields[name]
            removed = True
        if name in self.int_fields:
            del self.int_fields[name]
            removed = True
        if name in self.float_fields:
            del self.float_fields[name]
            removed = True
        if name in self.bool_fields:
            del self.bool_fields[name]
            removed = True
        if name in self.list_fields:
            del self.list_fields[name]
            removed = True
        return removed

    def get_all_field_names(self) -> list[str]:
        """Get all field names."""
        names: set[str] = set()
        names.update(self.string_fields.keys())
        names.update(self.int_fields.keys())
        names.update(self.float_fields.keys())
        names.update(self.bool_fields.keys())
        names.update(self.list_fields.keys())
        return sorted(names)

    def get_field_type(self, name: str) -> str | None:
        """Get the type of a field."""
        if name in self.string_fields:
            return "string"
        if name in self.int_fields:
            return "int"
        if name in self.float_fields:
            return "float"
        if name in self.bool_fields:
            return "bool"
        if name in self.list_fields:
            return "list"
        return None

    def clear_all_fields(self) -> None:
        """Clear all custom fields."""
        self.string_fields.clear()
        self.int_fields.clear()
        self.float_fields.clear()
        self.bool_fields.clear()
        self.list_fields.clear()

    def get_field_count(self) -> int:
        """Get total number of fields."""
        return (
            len(self.string_fields)
            + len(self.int_fields)
            + len(self.float_fields)
            + len(self.bool_fields)
            + len(self.list_fields)
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert all fields to a single dictionary."""
        result: dict[str, Any] = {}
        result.update(self.string_fields)
        result.update(self.int_fields)
        result.update(self.float_fields)
        result.update(self.bool_fields)
        result.update(self.list_fields)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelCustomFields":
        """Create from dictionary with type detection."""
        instance = cls()
        for key, value in data.items():
            instance.set_field(key, value)
        return instance

    def merge_fields(self, other: "ModelCustomFields") -> None:
        """Merge fields from another ModelCustomFields instance."""
        self.string_fields.update(other.string_fields)
        self.int_fields.update(other.int_fields)
        self.float_fields.update(other.float_fields)
        self.bool_fields.update(other.bool_fields)
        self.list_fields.update(other.list_fields)

    def copy_fields(self) -> "ModelCustomFields":
        """Create a copy of this instance."""
        return ModelCustomFields(
            string_fields=self.string_fields.copy(),
            int_fields=self.int_fields.copy(),
            float_fields=self.float_fields.copy(),
            bool_fields=self.bool_fields.copy(),
            list_fields=self.list_fields.copy(),
        )

    def get_fields_by_type(self, field_type: str) -> dict[str, Any]:
        """Get all fields of a specific type."""
        if field_type == "string":
            return self.string_fields.copy()
        if field_type == "int":
            return self.int_fields.copy()
        if field_type == "float":
            return self.float_fields.copy()
        if field_type == "bool":
            return self.bool_fields.copy()
        if field_type == "list":
            return self.list_fields.copy()
        return {}

    def validate_field_value(self, name: str, value: Any) -> bool:
        """Validate if a value is compatible with existing field type."""
        existing_type = self.get_field_type(name)
        if existing_type is None:
            return True  # New field, any type is valid

        # Check type compatibility
        return (
            (existing_type == "string" and isinstance(value, str))
            or (
                existing_type == "int"
                and isinstance(value, int)
                and not isinstance(value, bool)
            )
            or (
                existing_type == "float"
                and isinstance(value, int | float)
                and not isinstance(value, bool)
            )
            or (existing_type == "bool" and isinstance(value, bool))
            or (existing_type == "list" and isinstance(value, list))
        )


# Export for use
__all__ = ["ModelCustomFields"]
