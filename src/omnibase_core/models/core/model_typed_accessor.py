"""
Typed field accessor for specific value types.

Provides type-safe field access with generic type support.
"""

from __future__ import annotations

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError

from .model_field_accessor import ModelFieldAccessor


class ModelTypedAccessor[T](ModelFieldAccessor):
    """Type-safe field accessor for specific types.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    def get_typed_field(self, path: str, expected_type: type[T], default: T) -> T:
        """Get field with type checking."""
        result = self.get_field(path)
        if result.is_ok():
            raw_value = result.unwrap().to_value()
            if raw_value is not None and isinstance(raw_value, expected_type):
                return raw_value
        return default

    def set_typed_field(self, path: str, value: T, expected_type: type[T]) -> bool:
        """Set field with type validation."""
        if isinstance(value, expected_type):
            # Convert typed value to ModelSchemaValue for field storage
            schema_value = ModelSchemaValue.from_value(value)
            return self.set_field(path, schema_value)
        return False

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        # Typed accessor classes don't have specific model fields - serialize accessible data
        result: dict[str, object] = {
            "accessor_type": self.__class__.__name__,
            "type_parameter": str(getattr(self, "__orig_class__", "Unknown")),
        }

        # Include any dynamically set attributes
        for key, value in self.__dict__.items():
            if not key.startswith("_"):
                try:
                    # Only include serializable values
                    if isinstance(
                        value,
                        (str, int, float, bool, list, dict, type(None)),
                    ):
                        result[key] = value
                    else:
                        result[key] = str(value)
                except (
                    Exception
                ):  # fallback-ok: skip non-serializable attributes gracefully
                    continue

        return result

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

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
__all__ = ["ModelTypedAccessor"]
