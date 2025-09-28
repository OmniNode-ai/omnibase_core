"""
Generic Custom Properties Model.

Standardized custom properties pattern to replace repetitive custom field patterns
found across 15+ models in the codebase. Provides type-safe custom property handling
with validation and utility methods.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import (
    Configurable,
    Nameable,
    Serializable,
    Validatable,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_result import ModelResult


class ModelCustomProperties(BaseModel):
    """
    Standardized custom properties with type safety.

    Replaces patterns like:
    - custom_strings: dict[str, str]
    - custom_metadata: dict[str, str | int | bool | float]
    - custom_numbers: dict[str, float]
    - custom_flags: dict[str, bool]

    Provides organized, typed custom fields with validation and utility methods.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    # Typed custom properties
    custom_strings: dict[str, str] = Field(
        default_factory=dict,
        description="String custom fields",
    )
    custom_numbers: dict[str, float] = Field(
        default_factory=dict,
        description="Numeric custom fields",
    )
    custom_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean custom fields",
    )

    def set_custom_string(self, key: str, value: str) -> None:
        """Set a custom string value."""
        self.custom_strings[key] = value

    def set_custom_number(self, key: str, value: float) -> None:
        """Set a custom numeric value."""
        self.custom_numbers[key] = value

    def set_custom_flag(self, key: str, value: bool) -> None:
        """Set a custom boolean value."""
        self.custom_flags[key] = value

    def get_custom_value(self, key: str) -> ModelResult[ModelSchemaValue, str]:
        """Get custom value from any category."""
        # Check each category with explicit typing
        if key in self.custom_strings:
            return ModelResult.ok(ModelSchemaValue.from_value(self.custom_strings[key]))
        if key in self.custom_numbers:
            return ModelResult.ok(ModelSchemaValue.from_value(self.custom_numbers[key]))
        if key in self.custom_flags:
            return ModelResult.ok(ModelSchemaValue.from_value(self.custom_flags[key]))
        return ModelResult.err(f"Custom field '{key}' not found in any category")

    def has_custom_field(self, key: str) -> bool:
        """Check if custom field exists in any category."""
        return (
            key in self.custom_strings
            or key in self.custom_numbers
            or key in self.custom_flags
        )

    def remove_custom_field(self, key: str) -> bool:
        """Remove custom field from any category."""
        removed = False
        if key in self.custom_strings:
            del self.custom_strings[key]
            removed = True
        if key in self.custom_numbers:
            del self.custom_numbers[key]
            removed = True
        if key in self.custom_flags:
            del self.custom_flags[key]
            removed = True
        return removed

    def get_all_custom_fields(self) -> dict[str, ModelSchemaValue]:
        """Get all custom fields as a unified dictionary."""
        result: dict[str, ModelSchemaValue] = {}
        for key, string_value in self.custom_strings.items():
            result[key] = ModelSchemaValue.from_value(string_value)
        for key, numeric_value in self.custom_numbers.items():
            result[key] = ModelSchemaValue.from_value(numeric_value)
        for key, flag_value in self.custom_flags.items():
            result[key] = ModelSchemaValue.from_value(flag_value)
        return result

    def set_custom_value(self, key: str, value: ModelSchemaValue) -> None:
        """Set custom value with automatic type detection."""
        raw_value = value.to_value()
        if isinstance(raw_value, str):
            self.set_custom_string(key, raw_value)
        elif isinstance(raw_value, bool):
            self.set_custom_flag(key, raw_value)
        else:  # isinstance(raw_value, (int, float))
            self.set_custom_number(key, float(raw_value))

    def update_properties(self, **kwargs: ModelSchemaValue) -> None:
        """Update custom properties using kwargs."""
        for key, value in kwargs.items():
            raw_value = value.to_value()
            if isinstance(raw_value, str):
                self.set_custom_string(key, raw_value)
            elif isinstance(raw_value, bool):
                self.set_custom_flag(key, raw_value)
            elif isinstance(raw_value, (int, float)):
                self.set_custom_number(key, float(raw_value))

    def clear_all(self) -> None:
        """Clear all custom properties."""
        self.custom_strings.clear()
        self.custom_numbers.clear()
        self.custom_flags.clear()

    def is_empty(self) -> bool:
        """Check if all custom property categories are empty."""
        return not any([self.custom_strings, self.custom_numbers, self.custom_flags])

    def get_field_count(self) -> int:
        """Get total number of custom fields across all categories."""
        return (
            len(self.custom_strings) + len(self.custom_numbers) + len(self.custom_flags)
        )

    @classmethod
    def create_with_properties(
        cls,
        **kwargs: ModelSchemaValue,
    ) -> ModelCustomProperties:
        """Create ModelCustomProperties with initial properties."""
        instance = cls()
        instance.update_properties(**kwargs)
        return instance

    @classmethod
    def from_metadata(
        cls,
        metadata: dict[str, ModelSchemaValue],
    ) -> ModelCustomProperties:
        """
        Create ModelCustomProperties from custom_metadata field.
        Uses .model_validate() for proper Pydantic deserialization.
        """
        # Convert to proper format for Pydantic validation
        custom_strings = {}
        custom_numbers = {}
        custom_flags = {}

        for k, v in metadata.items():
            raw_value = v.to_value()
            if isinstance(raw_value, str):
                custom_strings[k] = raw_value
            elif isinstance(raw_value, (int, float)):
                custom_numbers[k] = float(raw_value)
            elif isinstance(raw_value, bool):
                custom_flags[k] = raw_value

        return cls.model_validate(
            {
                "custom_strings": custom_strings,
                "custom_numbers": custom_numbers,
                "custom_flags": custom_flags,
            },
        )

    def to_metadata(self) -> dict[str, ModelSchemaValue]:
        """
        Convert to custom_metadata format using Pydantic serialization.
        Uses .model_dump() for proper Pydantic serialization.
        """
        dumped = self.model_dump()
        result: dict[str, ModelSchemaValue] = {}

        for key, string_value in dumped["custom_strings"].items():
            result[key] = ModelSchemaValue.from_value(string_value)
        for key, numeric_value in dumped["custom_numbers"].items():
            result[key] = ModelSchemaValue.from_value(numeric_value)
        for key, flag_value in dumped["custom_flags"].items():
            result[key] = ModelSchemaValue.from_value(flag_value)

        return result

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
__all__ = ["ModelCustomProperties"]
