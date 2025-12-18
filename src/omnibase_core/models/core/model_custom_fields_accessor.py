"""
Generic custom fields accessor with comprehensive field management.

Provides generic type support and comprehensive field operations for managing
typed custom fields with automatic initialization and type safety.
"""

from __future__ import annotations

import copy
from typing import Any

from pydantic import Field, model_validator

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.types.constraints import PrimitiveValueType
from omnibase_core.types.type_serializable_value import SerializedDict

from .model_field_accessor import ModelFieldAccessor

# Type alias for schema values that can be stored in custom fields
# Simplified to PrimitiveValueType for ONEX compliance (removing List[Any] primitive soup)
SchemaValueType = PrimitiveValueType | None


class ModelCustomFieldsAccessor[T](ModelFieldAccessor):
    """Generic custom fields accessor with comprehensive field management."""

    # Typed field storage
    string_fields: dict[str, str] = Field(default_factory=dict)
    int_fields: dict[str, int] = Field(default_factory=dict)
    bool_fields: dict[str, bool] = Field(default_factory=dict)
    list_fields: dict[str, list[Any]] = Field(default_factory=dict)
    float_fields: dict[str, float] = Field(default_factory=dict)
    # Custom fields storage - can be overridden by subclasses to have default=None
    custom_fields: dict[str, PrimitiveValueType] | None = Field(default=None)

    # Pydantic configuration to allow extra fields
    model_config = {
        "extra": "allow",  # Allow dynamic fields
        "use_enum_values": False,
        "validate_assignment": False,  # Disable strict validation for dynamic fields
    }

    @model_validator(mode="before")
    @classmethod
    def validate_and_distribute_fields(cls, values: object) -> dict[str, object]:
        """Validate and distribute incoming fields to appropriate typed storages."""
        if not isinstance(values, dict):
            return {}

        # Create empty typed field storages, but only if they don't exist
        result = {
            "string_fields": values.get("string_fields", {}),
            "int_fields": values.get("int_fields", {}),
            "bool_fields": values.get("bool_fields", {}),
            "list_fields": values.get("list_fields", {}),
            "float_fields": values.get("float_fields", {}),
        }

        # Don't automatically create custom_fields - let it be None if not defined
        if "custom_fields" in values:
            result["custom_fields"] = values["custom_fields"]

        # Distribute values to appropriate typed storages
        for key, value in values.items():
            # Skip if this is already a typed field storage
            if key in result:
                result[key] = value
                continue

            # Distribute based on value type
            # NOTE: Check bool before int since bool is a subclass of int in Python
            if isinstance(value, bool):
                result["bool_fields"][key] = value
            elif isinstance(value, str):
                result["string_fields"][key] = value
            elif isinstance(value, int):
                result["int_fields"][key] = value
            elif isinstance(value, list):
                result["list_fields"][key] = value
            elif isinstance(value, float):
                result["float_fields"][key] = value
            elif isinstance(value, dict):
                # Convert dict to string representation
                result["string_fields"][key] = str(value)
            else:
                # Store as string fallback
                result["string_fields"][key] = str(value)

        return result

    def set_field(
        self,
        path: str,
        value: PrimitiveValueType | ModelSchemaValue | None,
    ) -> bool:
        """Set a field value with automatic type detection and storage."""
        try:
            # Handle nested field paths
            if "." in path:
                # Convert value to parent-compatible type if needed
                if value is None:
                    # Convert None to ModelSchemaValue for parent class compatibility
                    parent_value: PrimitiveValueType | ModelSchemaValue = (
                        ModelSchemaValue.from_value(value)
                    )
                elif isinstance(value, ModelSchemaValue):
                    parent_value = value
                else:
                    # For PrimitiveValueType (str, int, float, bool) - pass through directly
                    parent_value = value
                return super().set_field(path, parent_value)
            # Handle simple field names (no dots)
            # Store in appropriate typed field based on value type
            # Use runtime type checking to avoid MyPy type narrowing issues
            if value is None:
                # Handle None by storing as empty string
                self.string_fields[path] = ""
            elif isinstance(value, ModelSchemaValue):
                # Convert ModelSchemaValue to string representation
                self.string_fields[path] = str(value.to_value())
            else:
                # Runtime type checking for primitive values
                # NOTE: Check bool before int since bool is a subclass of int in Python
                value_type = type(value)
                if value_type is bool:
                    self.bool_fields[path] = value  # type: ignore[assignment]
                elif value_type is str:
                    self.string_fields[path] = value  # type: ignore[assignment]
                elif value_type is int:
                    self.int_fields[path] = value  # type: ignore[assignment]
                elif value_type is float:
                    self.float_fields[path] = value  # type: ignore[assignment]
                elif isinstance(value, list):
                    self.list_fields[path] = value
                else:
                    # Fallback to string storage for any other type
                    self.string_fields[path] = str(value)

            return True
        except Exception:  # fallback-ok: set_field method signature returns bool for success/failure rather than raising
            return False

    def get_field(self, path: str, default: Any = None) -> Any:
        """Get a field value from the appropriate typed storage.

        For simple field names, returns raw values from typed storages.
        For nested paths (containing '.'), returns ModelResult.
        """
        try:
            # Handle nested field paths - return ModelResult for dot notation support
            if "." in path:
                result = super().get_field(
                    path,
                    (
                        ModelSchemaValue.from_value(default)
                        if default is not None
                        else None
                    ),
                )
                return result  # Return ModelResult for nested paths

            # For simple field names, return raw values from typed storages
            # Check each typed field storage
            if path in self.string_fields:
                return self.string_fields[path]
            if path in self.int_fields:
                return self.int_fields[path]
            if path in self.bool_fields:
                return self.bool_fields[path]
            if path in self.list_fields:
                return self.list_fields[path]
            if path in self.float_fields:
                return self.float_fields[path]
            if (
                hasattr(self, "custom_fields")
                and getattr(self, "custom_fields", None) is not None
                and path in getattr(self, "custom_fields", {})
            ):
                custom_fields = getattr(self, "custom_fields", {})
                return custom_fields[path]
            return default
        except Exception:  # fallback-ok: get_field returns default value on error for graceful field access
            return default

    def get_string(self, key: str, default: str = "") -> str:
        """Get a string field value."""
        if key in self.string_fields:
            return self.string_fields[key]
        # Try to convert from other types
        value = self.get_field(key)
        if value is not None and not isinstance(value, str):
            return str(value) if value != default else default
        return value if isinstance(value, str) else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer field value."""
        if key in self.int_fields:
            return self.int_fields[key]
        # Try to convert from other types
        value = self.get_field(key)
        if value is not None and isinstance(value, int):
            return int(value)  # Explicit cast for type safety
        return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean field value."""
        if key in self.bool_fields:
            return self.bool_fields[key]
        # Try to convert from other types
        value = self.get_field(key)
        if value is not None and isinstance(value, bool):
            return bool(value)  # Explicit cast for type safety
        return default

    def get_list(self, key: str, default: list[Any] | None = None) -> list[Any]:
        """Get a list[Any]field value."""
        if default is None:
            default = []
        if key in self.list_fields:
            return self.list_fields[key]
        # Try to get from other types
        value = self.get_field(key)
        if value is not None and isinstance(value, list):
            return list(value)  # Explicit cast for type safety
        return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a float field value."""
        if key in self.float_fields:
            return self.float_fields[key]
        # Try to convert from other types
        value = self.get_field(key)
        if value is not None and isinstance(value, float):
            return float(value)  # Explicit cast for type safety
        return default

    def has_field(self, path: str) -> bool:
        """Check if a field exists in any typed storage."""
        if "." in path:
            return super().has_field(path)

        # Special case for custom_fields - return False if None, True if has any fields
        if path == "custom_fields":
            custom_fields = getattr(self, "custom_fields", None)
            return (
                hasattr(self, "custom_fields")
                and custom_fields is not None
                and len(custom_fields) > 0
            )

        return (
            path in self.string_fields
            or path in self.int_fields
            or path in self.bool_fields
            or path in self.list_fields
            or path in self.float_fields
            or (
                hasattr(self, "custom_fields")
                and getattr(self, "custom_fields", None) is not None
                and path in getattr(self, "custom_fields", {})
            )
        )

    def remove_field(self, path: str) -> bool:
        """Remove a field from the appropriate typed storage."""
        try:
            if "." in path:
                return super().remove_field(path)

            removed = False
            if path in self.string_fields:
                del self.string_fields[path]
                removed = True
            if path in self.int_fields:
                del self.int_fields[path]
                removed = True
            if path in self.bool_fields:
                del self.bool_fields[path]
                removed = True
            if path in self.list_fields:
                del self.list_fields[path]
                removed = True
            if path in self.float_fields:
                del self.float_fields[path]
                removed = True
            if (
                hasattr(self, "custom_fields")
                and getattr(self, "custom_fields", None) is not None
                and path in getattr(self, "custom_fields", {})
            ):
                custom_fields = getattr(self, "custom_fields", {})
                del custom_fields[path]
                removed = True
            return removed
        except Exception:  # fallback-ok: remove_field method signature returns bool for success/failure rather than raising
            return False

    def get_field_count(self) -> int:
        """Get the total number of fields across all typed storages."""
        custom_count = 0
        if hasattr(self, "custom_fields") and self.custom_fields is not None:
            custom_count = len(self.custom_fields)

        return (
            len(self.string_fields)
            + len(self.int_fields)
            + len(self.bool_fields)
            + len(self.list_fields)
            + len(self.float_fields)
            + custom_count
        )

    def get_all_field_names(self) -> list[str]:
        """Get all field names across all typed storages."""
        all_names: set[str] = set()
        all_names.update(self.string_fields.keys())
        all_names.update(self.int_fields.keys())
        all_names.update(self.bool_fields.keys())
        all_names.update(self.list_fields.keys())
        all_names.update(self.float_fields.keys())
        if (
            hasattr(self, "custom_fields")
            and getattr(self, "custom_fields", None) is not None
        ):
            custom_fields = getattr(self, "custom_fields", {})
            all_names.update(custom_fields.keys())
        return list(all_names)

    def clear_all_fields(self) -> None:
        """Clear all fields from all typed storages."""
        self.string_fields.clear()
        self.int_fields.clear()
        self.bool_fields.clear()
        self.list_fields.clear()
        self.float_fields.clear()
        if (
            hasattr(self, "custom_fields")
            and getattr(self, "custom_fields", None) is not None
        ):
            custom_fields = getattr(self, "custom_fields", {})
            custom_fields.clear()

    def get_field_type(self, key: str) -> str:
        """Get the type of a field."""
        if key in self.string_fields:
            return "string"
        if key in self.int_fields:
            return "int"
        if key in self.bool_fields:
            return "bool"
        if key in self.list_fields:
            return "list[Any]"
        if key in self.float_fields:
            return "float"
        if hasattr(self, "custom_fields") and key in getattr(
            self,
            "custom_fields",
            {},
        ):
            return "custom"
        return "unknown"

    def validate_field_value(self, key: str, value: SchemaValueType) -> bool:
        """Validate if a value is compatible with a field's existing type."""
        if not self.has_field(key):
            return True  # New fields are always valid

        if value is None:
            return True  # None is always acceptable

        field_type = self.get_field_type(key)

        # Use runtime type checking to avoid MyPy type narrowing issues
        value_type = type(value)

        if field_type == "string":
            return value_type is str
        if field_type == "int":
            return value_type is int
        if field_type == "bool":
            return value_type is bool
        if field_type == "float":
            return value_type is float
        if field_type == "list[Any]":
            return isinstance(value, list)
        if field_type == "custom":
            return True  # Custom fields accept any type
        return False

    def get_fields_by_type(self, field_type: str) -> dict[str, object]:
        """Get all fields of a specific type."""
        if field_type == "string":
            return dict(self.string_fields)
        if field_type == "int":
            return dict(self.int_fields)
        if field_type == "bool":
            return dict(self.bool_fields)
        if field_type == "list[Any]":
            return dict(self.list_fields)
        if field_type == "float":
            return dict(self.float_fields)
        if field_type == "custom":
            custom_fields = getattr(self, "custom_fields", {})
            return dict(custom_fields) if custom_fields else {}
        return {}

    def copy_fields(self) -> ModelCustomFieldsAccessor[T]:
        """Create a deep copy of this field accessor."""
        new_instance = self.__class__()
        new_instance.string_fields = copy.deepcopy(self.string_fields)
        new_instance.int_fields = copy.deepcopy(self.int_fields)
        new_instance.bool_fields = copy.deepcopy(self.bool_fields)
        new_instance.list_fields = copy.deepcopy(self.list_fields)
        new_instance.float_fields = copy.deepcopy(self.float_fields)

        # Only copy custom_fields if it exists
        if (
            hasattr(self, "custom_fields")
            and getattr(self, "custom_fields", None) is not None
        ):
            custom_fields = getattr(self, "custom_fields", {})
            new_instance.custom_fields = copy.deepcopy(custom_fields)

        return new_instance

    def merge_fields(self, other: ModelCustomFieldsAccessor[T]) -> None:
        """Merge fields from another accessor into this one."""
        self.string_fields.update(other.string_fields)
        self.int_fields.update(other.int_fields)
        self.bool_fields.update(other.bool_fields)
        self.list_fields.update(other.list_fields)
        self.float_fields.update(other.float_fields)

        # Only merge custom_fields if both objects have them
        self_custom_fields = getattr(self, "custom_fields", None)
        other_custom_fields = getattr(other, "custom_fields", None)

        if (
            hasattr(self, "custom_fields")
            and self_custom_fields is not None
            and hasattr(other, "custom_fields")
            and other_custom_fields is not None
        ):
            self_custom_fields.update(other_custom_fields)
        elif hasattr(other, "custom_fields") and other_custom_fields is not None:
            # Initialize our custom_fields if other has them but we don't
            self.custom_fields = copy.deepcopy(other_custom_fields)

    def model_dump(self, exclude_none: bool = False, **kwargs: Any) -> SerializedDict:
        """Override model_dump to include all field data."""
        data: SerializedDict = {}

        # Add all fields to the output
        for key in self.get_all_field_names():
            value = self.get_field(key)
            if not exclude_none or value is not None:
                data[key] = value

        return data

    # Custom field convenience methods
    def get_custom_field(
        self,
        key: str,
        default: SchemaValueType = None,
    ) -> SchemaValueType:
        """Get a custom field value as raw value. Returns raw value or default."""
        if (
            hasattr(self, "custom_fields")
            and self.custom_fields is not None
            and key in self.custom_fields
        ):
            return self.custom_fields[key]
        return default

    def get_custom_field_value(
        self,
        key: str,
        default: SchemaValueType = None,
    ) -> SchemaValueType:
        """Get custom field value as raw value. Returns raw value or default."""
        return self.get_custom_field(key, default)

    def set_custom_field(
        self,
        key: str,
        value: PrimitiveValueType | ModelSchemaValue | None,
    ) -> bool:
        """Set a custom field value. Accepts raw values or ModelSchemaValue."""
        try:
            # Initialize custom_fields if it's None with explicit type annotation
            if not hasattr(self, "custom_fields") or self.custom_fields is None:
                # Explicitly type the dictionary to avoid MyPy inference issues

                self.custom_fields: dict[str, PrimitiveValueType] = {}

            # Store raw values directly in custom_fields
            if isinstance(value, ModelSchemaValue):
                raw_value = value.to_value()
                # Ensure raw_value is compatible with PrimitiveValueType
                if not isinstance(raw_value, (str, int, float, bool, list, type(None))):
                    raw_value = str(raw_value)  # Convert unsupported types to string
            else:
                raw_value = value

            # Cast to PrimitiveValueType to satisfy type checker
            # Since PrimitiveValueType is object, this is safe at runtime
            self.custom_fields[key] = raw_value
            return True
        except Exception:  # fallback-ok: set_custom_field method signature returns bool for success/failure rather than raising
            return False

    def has_custom_field(self, key: str) -> bool:
        """Check if a custom field exists."""
        return (
            hasattr(self, "custom_fields")
            and self.custom_fields is not None
            and key in self.custom_fields
        )

    def remove_custom_field(self, key: str) -> bool:
        """Remove a custom field."""
        try:
            if (
                hasattr(self, "custom_fields")
                and self.custom_fields is not None
                and key in self.custom_fields
            ):
                del self.custom_fields[key]
                return True
            return False
        except Exception:  # fallback-ok: remove_custom_field method signature returns bool for success/failure rather than raising
            return False

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: protocol method must return bool, not raise
            return False

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:  # fallback-ok: protocol method must return bool, not raise
            return False

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return


# Export for use
__all__ = ["ModelCustomFieldsAccessor"]
