"""
Custom fields accessor with initialization support.

Specialized accessor for managing custom fields with automatic initialization.
"""

from .model_field_accessor import ModelFieldAccessor


class ModelCustomFieldsAccessor(ModelFieldAccessor):
    """Specialized accessor for custom fields with initialization."""

    def get_custom_field(
        self, key: str, default: str | int | float | bool | list[str] | None = None
    ) -> str | int | float | bool | list[str] | None:
        """Get a custom field value, initializing custom_fields if needed."""
        if not self.has_field("custom_fields"):
            return default
        return self.get_field(f"custom_fields.{key}", default)

    def set_custom_field(
        self, key: str, value: str | int | float | bool | list[str]
    ) -> bool:
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


# Export for use
__all__ = ["ModelCustomFieldsAccessor"]
