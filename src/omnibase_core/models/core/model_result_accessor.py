"""
Result field accessor for CLI results and output data.

Specialized accessor for handling CLI execution results and metadata.
"""

from __future__ import annotations

from typing import Any

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_result import ModelResult

from .model_field_accessor import ModelFieldAccessor


class ModelResultAccessor(ModelFieldAccessor):
    """Specialized accessor for CLI results and output data.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    def get_result_value(
        self,
        key: str,
        default: ModelSchemaValue | None = None,
    ) -> ModelResult[ModelSchemaValue, str]:
        """Get result value from results or metadata fields."""
        # Try results first
        results_value = self.get_field(f"results.{key}")
        if results_value.is_ok():
            return results_value

        # Try metadata second
        metadata_value = self.get_field(f"metadata.{key}")
        if metadata_value.is_ok():
            return metadata_value

        # If both failed, return default if provided, otherwise error
        if default is not None:
            return ModelResult.ok(default)
        return ModelResult.err(f"Result value '{key}' not found in results or metadata")

    def set_result_value(self, key: str, value: ModelSchemaValue) -> bool:
        """Set result value in results field."""
        return self.set_field(f"results.{key}", value)

    def set_metadata_value(self, key: str, value: ModelSchemaValue) -> bool:
        """Set metadata value in metadata field."""
        return self.set_field(f"metadata.{key}", value)

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
        # Accessor classes don't have specific model fields - serialize accessible data
        result: dict[str, Any] = {
            "accessor_type": self.__class__.__name__,
        }

        # Include any dynamically set attributes
        for key, value in self.__dict__.items():
            if not key.startswith("_"):
                try:
                    # Only include serializable values
                    if isinstance(
                        value, (str, int, float, bool, list, dict, type(None))
                    ):
                        result[key] = value
                    else:
                        result[key] = str(value)
                except Exception:
                    # Skip any attributes that can't be serialized
                    continue

        return result

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
__all__ = ["ModelResultAccessor"]
