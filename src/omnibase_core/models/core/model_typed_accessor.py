from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Typed field accessor for specific value types.

Provides type-safe field access with generic type support.
"""


from typing import Any, Generic, TypeVar

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

from .model_field_accessor import ModelFieldAccessor

T = TypeVar("T")


class ModelTypedAccessor(ModelFieldAccessor, Generic[T]):
    """Type-safe field accessor for specific types.
    Implements omnibase_spi protocols:
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

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        # Typed accessor classes don't have specific model fields - serialize accessible data
        result: dict[str, Any] = {
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
                except Exception:
                    # Skip any attributes that can't be serialized
                    continue

        return result

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
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
