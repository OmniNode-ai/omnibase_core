"""
Custom fields accessor with initialization support.

Specialized accessor for managing custom fields with automatic initialization.
"""

from __future__ import annotations

from ..common.model_schema_value import ModelSchemaValue
from ..infrastructure.model_result import Result
from .model_field_accessor import ModelFieldAccessor


class ModelCustomFieldsAccessor(ModelFieldAccessor):
    """Specialized accessor for custom fields with initialization."""

    def get_custom_field(
        self,
        key: str,
        default: ModelSchemaValue | None = None,
    ) -> Result[ModelSchemaValue, str]:
        """Get a custom field value, initializing custom_fields if needed."""
        if not self.has_field("custom_fields"):
            if default is not None:
                return Result.ok(default)
            return Result.err(
                f"Custom fields not initialized and no default provided for key '{key}'"
            )
        return self.get_field(f"custom_fields.{key}", default)

    def set_custom_field(self, key: str, value: ModelSchemaValue) -> bool:
        """Set a custom field value, initializing custom_fields if needed."""
        # Initialize custom_fields if it doesn't exist
        if not self.has_field("custom_fields"):
            # Use setattr directly for dict initialization
            custom_fields: dict[str, ModelSchemaValue] = {}
            self.custom_fields = custom_fields
        return self.set_field(f"custom_fields.{key}", value)

    def has_custom_field(self, key: str) -> bool:
        """Check if a custom field exists."""
        return self.has_field(f"custom_fields.{key}")

    def remove_custom_field(self, key: str) -> bool:
        """Remove a custom field."""
        return self.remove_field(f"custom_fields.{key}")


# Export for use
__all__ = ["ModelCustomFieldsAccessor"]
