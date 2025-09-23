"""
Typed field accessor for specific value types.

Provides type-safe field access with generic type support.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from omnibase_core.models.common.model_schema_value import ModelSchemaValue

from .model_field_accessor import ModelFieldAccessor

T = TypeVar("T")


class ModelTypedAccessor(ModelFieldAccessor, Generic[T]):
    """Type-safe field accessor for specific types."""

    def get_typed_field(self, path: str, expected_type: type[T], default: T) -> T:
        """Get field with type checking."""
        value = self.get_field(path)
        if value is not None and isinstance(value, expected_type):
            return value
        return default

    def set_typed_field(self, path: str, value: T, expected_type: type[T]) -> bool:
        """Set field with type validation."""
        if isinstance(value, expected_type):
            # Convert typed value to ModelSchemaValue for field storage
            schema_value = ModelSchemaValue.from_value(value)
            return self.set_field(path, schema_value)
        return False


# Export for use
__all__ = ["ModelTypedAccessor"]
