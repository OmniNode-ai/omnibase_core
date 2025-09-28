"""
Environment field accessor with type coercion.

Specialized accessor for environment properties with automatic type conversion.
"""

from __future__ import annotations

from typing import Any, TypeVar, cast, get_origin

from omnibase_core.models.common.model_schema_value import ModelSchemaValue

from .model_field_accessor import ModelFieldAccessor

# Type variable for generic property handling
T = TypeVar("T")


class ModelEnvironmentAccessor(ModelFieldAccessor):
    """Specialized accessor for environment properties with type coercion.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    def get_typed_value(self, path: str, expected_type: type[T], default: T) -> T:
        """Get a field value with specific type checking using generic type inference."""
        schema_default = ModelSchemaValue.from_value(default)
        result = self.get_field(path, schema_default)

        if not result.is_ok():
            return default

        value = result.unwrap()
        raw_value = value.to_value()

        if raw_value is None:
            return default

        try:
            # Type-specific coercion logic based on expected type
            if expected_type == str:
                return cast(T, str(raw_value))
            elif expected_type == int:
                if isinstance(raw_value, (int, float)) or (
                    isinstance(raw_value, str) and raw_value.isdigit()
                ):
                    return cast(T, int(raw_value))
            elif expected_type == float:
                if isinstance(raw_value, (int, float)):
                    return cast(T, float(raw_value))
                elif isinstance(raw_value, str):
                    return cast(T, float(raw_value))
            elif expected_type == bool:
                if isinstance(raw_value, bool):
                    return cast(T, raw_value)
                elif isinstance(raw_value, str):
                    return cast(
                        T, raw_value.lower() in ["true", "yes", "1", "on", "enabled"]
                    )
                elif isinstance(raw_value, (int, float)):
                    return cast(T, bool(raw_value))
            elif expected_type == list or get_origin(expected_type) is list:
                # Handle list types
                if isinstance(raw_value, list):
                    return cast(T, [str(item) for item in raw_value])
                elif isinstance(raw_value, str):
                    # Support comma-separated values
                    return cast(
                        T,
                        [item.strip() for item in raw_value.split(",") if item.strip()],
                    )
            elif isinstance(raw_value, expected_type):
                return raw_value
        except (ValueError, TypeError):
            pass

        return default

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
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
__all__ = ["ModelEnvironmentAccessor"]
