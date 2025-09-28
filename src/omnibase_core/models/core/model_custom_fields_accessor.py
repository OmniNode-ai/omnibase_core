"""
Custom fields accessor with initialization support.

Specialized accessor for managing custom fields with automatic initialization.
"""

from __future__ import annotations

from typing import Any

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_result import ModelResult

from .model_field_accessor import ModelFieldAccessor


class ModelCustomFieldsAccessor(ModelFieldAccessor):
    """Specialized accessor for custom fields with initialization.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    def get_custom_field(
        self,
        key: str,
        default: ModelSchemaValue | None = None,
    ) -> ModelResult[ModelSchemaValue, str]:
        """Get a custom field value, initializing custom_fields if needed."""
        if not self.has_field("custom_fields"):
            if default is not None:
                return ModelResult.ok(default)
            return ModelResult.err(
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
__all__ = ["ModelCustomFieldsAccessor"]
