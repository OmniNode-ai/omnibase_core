"""
Generic field accessor pattern for replacing dict-like interfaces.

Provides unified field access across CLI, Config, and Data domains with
dot notation support and type safety.
"""

from typing import Any, Dict, Generic, Optional, TypeVar, Union, cast

from pydantic import BaseModel, Field

T = TypeVar("T")


class ModelFieldAccessor(BaseModel):
    """Generic field accessor with dot notation support and type safety."""

    def get_field(self, path: str, default: Any = None) -> Any:
        """Get field using dot notation: 'metadata.custom_fields.key'"""
        try:
            obj: Any = self
            for part in path.split("."):
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif (
                    hasattr(obj, "__getitem__")
                    and hasattr(obj, "__contains__")
                    and part in obj
                ):
                    obj = obj[part]
                else:
                    return default
            return obj
        except (AttributeError, KeyError, TypeError):
            return default

    def set_field(self, path: str, value: Any) -> bool:
        """Set field using dot notation."""
        try:
            parts = path.split(".")
            obj: Any = self

            # Navigate to parent object
            for part in parts[:-1]:
                if hasattr(obj, part):
                    next_obj = getattr(obj, part)
                    # If the attribute exists but is None, initialize it as a dict
                    if next_obj is None:
                        try:
                            setattr(obj, part, {})
                            next_obj = getattr(obj, part)
                        except (AttributeError, TypeError):
                            return False
                    obj = next_obj
                elif hasattr(obj, "__getitem__") and hasattr(obj, "__setitem__"):
                    if hasattr(obj, "__contains__") and part not in obj:
                        obj[part] = {}
                    obj = obj[part]
                else:
                    return False

            # Set the final value
            final_key = parts[-1]
            # First try setting as attribute if the object has the field (even if None)
            # This handles Pydantic model fields that are initially None
            if hasattr(obj, final_key) or hasattr(obj, "__dict__"):
                try:
                    setattr(obj, final_key, value)
                    return True
                except (AttributeError, TypeError):
                    pass
            # Fall back to dict-like access
            if hasattr(obj, "__setitem__"):
                obj[final_key] = value
                return True

            return False
        except (AttributeError, KeyError, TypeError):
            return False

    def has_field(self, path: str) -> bool:
        """Check if field exists using dot notation."""
        try:
            obj: Any = self
            for part in path.split("."):
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif (
                    hasattr(obj, "__getitem__")
                    and hasattr(obj, "__contains__")
                    and part in obj
                ):
                    obj = obj[part]
                else:
                    return False
            return True
        except (AttributeError, KeyError, TypeError):
            return False

    def remove_field(self, path: str) -> bool:
        """Remove field using dot notation."""
        try:
            parts = path.split(".")
            obj: Any = self

            # Navigate to parent object
            for part in parts[:-1]:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif (
                    hasattr(obj, "__getitem__")
                    and hasattr(obj, "__contains__")
                    and part in obj
                ):
                    obj = obj[part]
                else:
                    return False

            # Remove the final field
            final_key = parts[-1]
            if hasattr(obj, final_key):
                delattr(obj, final_key)
            elif (
                hasattr(obj, "__delitem__")
                and hasattr(obj, "__contains__")
                and final_key in obj
            ):
                del obj[final_key]
            else:
                return False

            return True
        except (AttributeError, KeyError, TypeError):
            return False


# Typed accessor for specific value types
class ModelTypedAccessor(ModelFieldAccessor, Generic[T]):
    """Type-safe field accessor for specific types."""

    def get_typed_field(
        self, path: str, expected_type: type[T], default: T | None = None
    ) -> T | None:
        """Get field with type checking."""
        value = self.get_field(path)
        if value is not None and isinstance(value, expected_type):
            return cast(T, value)
        return default

    def set_typed_field(self, path: str, value: T, expected_type: type[T]) -> bool:
        """Set field with type validation."""
        if isinstance(value, expected_type):
            return self.set_field(path, value)
        return False


# Specialized accessors for common patterns
class ModelEnvironmentAccessor(ModelFieldAccessor):
    """Specialized accessor for environment properties with type coercion."""

    def get_string(self, path: str, default: str = "") -> str:
        """Get string value with type coercion."""
        value = self.get_field(path, default)
        return str(value) if value is not None else default

    def get_int(self, path: str, default: int = 0) -> int:
        """Get integer value with type coercion."""
        value = self.get_field(path, default)
        if isinstance(value, (int, float)) or (
            isinstance(value, str) and value.isdigit()
        ):
            return int(value)
        return default

    def get_float(self, path: str, default: float = 0.0) -> float:
        """Get float value with type coercion."""
        value = self.get_field(path, default)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        return default

    def get_bool(self, path: str, default: bool = False) -> bool:
        """Get boolean value with type coercion."""
        value = self.get_field(path, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ["true", "yes", "1", "on", "enabled"]
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    def get_list(self, path: str, default: list[str] | None = None) -> list[str]:
        """Get list value with type coercion."""
        if default is None:
            default = []
        value = self.get_field(path, default)
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            # Support comma-separated values
            return [item.strip() for item in value.split(",") if item.strip()]
        return default


class ModelResultAccessor(ModelFieldAccessor):
    """Specialized accessor for CLI results and output data."""

    def get_result_value(
        self, key: str, default: str | int | bool | float | None = None
    ) -> str | int | bool | float | None:
        """Get result value from results or metadata fields."""
        # Try results first
        value = self.get_field(f"results.{key}")
        if value is not None and isinstance(value, (str, int, bool, float)):
            return cast(Union[str, int, bool, float], value)

        # Try metadata second
        value = self.get_field(f"metadata.{key}")
        if value is not None and isinstance(value, (str, int, bool, float)):
            return cast(Union[str, int, bool, float], value)

        return default

    def set_result_value(self, key: str, value: str | int | bool | float) -> bool:
        """Set result value in results field."""
        return self.set_field(f"results.{key}", value)

    def set_metadata_value(self, key: str, value: str | int | bool) -> bool:
        """Set metadata value in metadata field."""
        return self.set_field(f"metadata.{key}", value)


class ModelCustomFieldsAccessor(ModelFieldAccessor):
    """Specialized accessor for custom fields with initialization."""

    def get_custom_field(self, key: str, default: Any = None) -> Any:
        """Get a custom field value, initializing custom_fields if needed."""
        if not self.has_field("custom_fields"):
            return default
        return self.get_field(f"custom_fields.{key}", default)

    def set_custom_field(self, key: str, value: Any) -> bool:
        """Set a custom field value, initializing custom_fields if needed."""
        # Initialize custom_fields if it doesn't exist
        if not self.has_field("custom_fields"):
            self.set_field("custom_fields", {})
        return self.set_field(f"custom_fields.{key}", value)

    def has_custom_field(self, key: str) -> bool:
        """Check if a custom field exists."""
        return self.has_field(f"custom_fields.{key}")

    def remove_custom_field(self, key: str) -> bool:
        """Remove a custom field."""
        return self.remove_field(f"custom_fields.{key}")


# Export all accessor classes
__all__ = [
    "ModelFieldAccessor",
    "ModelTypedAccessor",
    "ModelEnvironmentAccessor",
    "ModelResultAccessor",
    "ModelCustomFieldsAccessor",
]
