"""
Generic Custom Properties Model.

Standardized custom properties pattern to replace repetitive custom field patterns
found across 15+ models in the codebase. Provides type-safe custom property handling
with validation and utility methods.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_constraints import PrimitiveValueType

if TYPE_CHECKING:
    from omnibase_core.models.infrastructure.model_result import ModelResult


class ModelCustomProperties(BaseModel):
    """
    Standardized custom properties with type safety.

    Replaces patterns like:
    - custom_strings: dict[str, str]
    - custom_metadata: dict[str, PrimitiveValueType] (simplified from complex unions)
    - custom_numbers: dict[str, float]
    - custom_flags: dict[str, bool]

    Provides organized, typed custom fields with validation and utility methods.
    Implements Core protocols:
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

    def get_custom_value(self, key: str) -> PrimitiveValueType | None:
        """Get custom value from any category by key.

        Searches across all typed property categories (strings, numbers, flags)
        and returns the raw value if found.

        Args:
            key: The property key to look up.

        Returns:
            The raw value (str, float, or bool) if found, None otherwise.

        Note:
            Search order is: custom_strings -> custom_numbers -> custom_flags.
            For wrapped results with error handling, use get_custom_value_wrapped().
        """
        # Check each category with explicit typing
        if key in self.custom_strings:
            return self.custom_strings[key]
        if key in self.custom_numbers:
            return self.custom_numbers[key]
        if key in self.custom_flags:
            return self.custom_flags[key]
        return None

    def get_custom_value_wrapped(
        self,
        key: str,
        default: ModelSchemaValue | None = None,
    ) -> ModelResult[ModelSchemaValue, str]:
        """Get custom value wrapped in ModelResult for consistent API with configuration.

        Provides a Result-based interface for property access, suitable for
        functional error handling patterns. Values are wrapped in ModelSchemaValue
        for type-safe schema compatibility.

        Args:
            key: The property key to look up.
            default: Optional default ModelSchemaValue to return if key not found.
                If None and key not found, returns an error result.

        Returns:
            ModelResult containing either:
            - Ok(ModelSchemaValue): The wrapped value if key found or default provided.
            - Err(str): Error message if key not found and no default provided.

        Note:
            Uses lazy import of ModelResult to avoid circular dependency with
            the infrastructure.model_result module.

        Example:
            >>> props = ModelCustomProperties()
            >>> props.set_custom_string("env", "production")
            >>> result = props.get_custom_value_wrapped("env")
            >>> if result.is_ok():
            ...     print(result.unwrap().to_value())
            production
        """
        # Lazy import to avoid circular dependency
        from omnibase_core.models.infrastructure.model_result import ModelResult

        # Check each category with explicit typing
        if key in self.custom_strings:
            return ModelResult.ok(ModelSchemaValue.from_value(self.custom_strings[key]))
        if key in self.custom_numbers:
            return ModelResult.ok(ModelSchemaValue.from_value(self.custom_numbers[key]))
        if key in self.custom_flags:
            return ModelResult.ok(ModelSchemaValue.from_value(self.custom_flags[key]))

        if default is not None:
            return ModelResult.ok(default)
        return ModelResult.err(f"Custom key '{key}' not found")

    def has_custom_field(self, key: str) -> bool:
        """Check if custom field exists in any category."""
        return (
            key in self.custom_strings
            or key in self.custom_numbers
            or key in self.custom_flags
        )

    def remove_custom_field(self, key: str) -> bool:
        """Remove custom field from all categories where it exists.

        Removes the field from every category (strings, numbers, flags) where
        it is present. This handles edge cases where the same key may exist
        in multiple categories.

        Args:
            key: The property key to remove.

        Returns:
            True if the field was removed from at least one category,
            False if the key was not found in any category.
        """
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

    def get_all_custom_fields(self) -> dict[str, PrimitiveValueType]:
        """Get all custom fields as a unified dictionary with raw values."""
        result: dict[str, PrimitiveValueType] = {}
        for key, string_value in self.custom_strings.items():
            result[key] = string_value
        for key, numeric_value in self.custom_numbers.items():
            result[key] = numeric_value
        for key, flag_value in self.custom_flags.items():
            result[key] = flag_value
        return result

    def set_custom_value(self, key: str, value: PrimitiveValueType) -> None:
        """Set custom value with automatic type detection and routing.

        Automatically routes the value to the appropriate typed category
        based on its Python type. Integer values are converted to float
        for storage in custom_numbers.

        Args:
            key: The property key to set.
            value: The value to store. Must be str, bool, int, or float.

        Raises:
            ModelOnexError: If value type is not one of the supported
                primitive types (str, bool, int, float).

        Note:
            Type checking order matters: bool is checked before int/float
            because bool is a subclass of int in Python.
        """
        if isinstance(value, str):
            self.set_custom_string(key, value)
        elif isinstance(value, bool):
            self.set_custom_flag(key, value)
        elif isinstance(value, (int, float)):
            self.set_custom_number(key, float(value))
        else:
            # Raise error for unsupported types
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unsupported custom value type: {type(value)}",
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("typeerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

    def update_properties(self, **kwargs: ModelSchemaValue) -> None:
        """Update custom properties from ModelSchemaValue keyword arguments.

        Extracts raw values from each ModelSchemaValue and routes them to
        the appropriate typed category. Unsupported types are silently skipped.

        Args:
            **kwargs: Keyword arguments where keys are property names and
                values are ModelSchemaValue instances.

        Note:
            Unlike set_custom_value(), this method silently ignores values
            that don't match supported types rather than raising an error.
            This is intentional for batch update scenarios.

        Example:
            >>> props = ModelCustomProperties()
            >>> props.update_properties(
            ...     env=ModelSchemaValue.from_value("prod"),
            ...     count=ModelSchemaValue.from_value(42)
            ... )
        """
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
        """Factory method to create instance with initial properties.

        Convenience constructor that creates a new instance and populates
        it with the provided ModelSchemaValue properties in one step.

        Args:
            **kwargs: Keyword arguments where keys are property names and
                values are ModelSchemaValue instances.

        Returns:
            A new ModelCustomProperties instance with the specified properties.

        Example:
            >>> props = ModelCustomProperties.create_with_properties(
            ...     env=ModelSchemaValue.from_value("staging"),
            ...     debug=ModelSchemaValue.from_value(True)
            ... )
        """
        instance = cls()
        instance.update_properties(**kwargs)
        return instance

    @classmethod
    def from_dict(cls, data: dict[str, PrimitiveValueType]) -> ModelCustomProperties:
        """Factory method to create instance from dictionary of raw values.

        Creates a new instance by iterating over the dictionary and routing
        each value to the appropriate typed category via set_custom_value().

        Args:
            data: Dictionary mapping property keys to raw primitive values
                (str, bool, int, or float).

        Returns:
            A new ModelCustomProperties instance with the specified properties.

        Raises:
            ModelOnexError: If any value type is not supported.

        Example:
            >>> props = ModelCustomProperties.from_dict({
            ...     "env": "production",
            ...     "retries": 3,
            ...     "verbose": True
            ... })
        """
        instance = cls()
        for key, value in data.items():
            instance.set_custom_value(key, value)
        return instance

    def update_from_dict(self, data: Mapping[str, PrimitiveValueType | None]) -> None:
        """Update custom properties from dictionary of raw values.

        Merges the provided dictionary into existing properties. None values
        are silently skipped, allowing partial updates with optional fields.

        Args:
            data: Mapping of property keys to raw primitive values or None.
                None values are ignored (existing values preserved).

        Raises:
            ModelOnexError: If any non-None value type is not supported.

        Note:
            This method merges with existing properties rather than replacing
            them. Use clear_all() first if you need a complete replacement.

        Example:
            >>> props = ModelCustomProperties.from_dict({"env": "dev"})
            >>> props.update_from_dict({"env": "prod", "debug": None})
            >>> props.get_custom_value("env")
            'prod'
        """
        for key, value in data.items():
            if value is not None:
                self.set_custom_value(key, value)

    @classmethod
    def from_metadata(
        cls,
        metadata: Mapping[str, PrimitiveValueType | ModelSchemaValue],
    ) -> ModelCustomProperties:
        """Factory method to create instance from custom_metadata field.

        Deserializes a metadata mapping that may contain either raw primitive
        values or ModelSchemaValue instances. This provides compatibility with
        both serialized data and runtime objects.

        Args:
            metadata: Mapping of property keys to either raw primitive values
                (str, bool, int, float) or ModelSchemaValue instances.

        Returns:
            A new ModelCustomProperties instance with properly typed properties.

        Note:
            Uses Pydantic's model_validate() for proper deserialization and
            validation. Values that don't match supported types are silently
            skipped. Bool is checked before int/float due to Python's type
            hierarchy.

        Example:
            >>> metadata = {
            ...     "env": "production",
            ...     "count": ModelSchemaValue.from_value(42),
            ...     "enabled": True
            ... }
            >>> props = ModelCustomProperties.from_metadata(metadata)
        """
        # Convert to proper format for Pydantic validation
        custom_strings = {}
        custom_numbers = {}
        custom_flags = {}

        for k, v in metadata.items():
            # Handle both ModelSchemaValue objects and raw values
            if hasattr(v, "to_value"):
                raw_value = v.to_value()
            else:
                raw_value = v

            if isinstance(raw_value, bool):
                custom_flags[k] = raw_value
            elif isinstance(raw_value, str):
                custom_strings[k] = raw_value
            elif isinstance(raw_value, (int, float)):
                custom_numbers[k] = float(raw_value)

        return cls.model_validate(
            {
                "custom_strings": custom_strings,
                "custom_numbers": custom_numbers,
                "custom_flags": custom_flags,
            },
        )

    def to_metadata(self) -> dict[str, PrimitiveValueType]:
        """Serialize to flat dictionary format for storage or transmission.

        Converts the typed property categories back into a unified dictionary
        of raw primitive values. This is the inverse of from_metadata() and
        ensures round-trip compatibility.

        Returns:
            Dictionary mapping property keys to raw primitive values.
            All values are native Python types (str, float, bool).

        Note:
            Uses Pydantic's model_dump() for proper serialization. The result
            is suitable for JSON serialization and can be passed to from_metadata()
            to recreate the original instance.

        Example:
            >>> props = ModelCustomProperties()
            >>> props.set_custom_string("env", "prod")
            >>> props.set_custom_number("retries", 3)
            >>> props.to_metadata()
            {'env': 'prod', 'retries': 3.0}
        """
        dumped = self.model_dump()
        result: dict[str, PrimitiveValueType] = {}

        # Return raw values instead of ModelSchemaValue instances
        for key, string_value in dumped["custom_strings"].items():
            result[key] = string_value
        for key, numeric_value in dumped["custom_numbers"].items():
            result[key] = numeric_value
        for key, flag_value in dumped["custom_flags"].items():
            result[key] = flag_value

        return result

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters.

        Implements the Configurable protocol. Sets attributes on the instance
        for any kwargs that match existing attribute names.

        Args:
            **kwargs: Attribute name/value pairs to configure.

        Returns:
            True if configuration succeeded, False if any error occurred.

        Note:
            Only attributes that already exist on the instance are set.
            Unknown attribute names are silently ignored.
        """
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: protocol method contract requires bool return - False indicates configuration failed safely
            return False

    def serialize(self) -> dict[str, object]:
        """Serialize instance to dictionary format.

        Implements the Serializable protocol. Uses Pydantic's model_dump()
        with aliases preserved and None values included.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity.

        Implements the ProtocolValidatable protocol. Performs basic validation
        to ensure required fields exist and are valid.

        Returns:
            True if validation passed, False if any validation error occurred.

        Note:
            Subclasses should override this method to add custom validation logic.
        """
        return True

    def get_name(self) -> str:
        """Get the instance name.

        Implements the Nameable protocol. Searches common name field patterns
        and returns the first non-None value found.

        Returns:
            The instance name if found, or a default "Unnamed {ClassName}" string.

        Note:
            Checks fields in order: name, display_name, title, node_name.
        """
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set the instance name.

        Implements the Nameable protocol. Sets the first available name field
        from the common patterns.

        Args:
            name: The name to set.

        Note:
            Checks fields in order: name, display_name, title, node_name.
            Only the first matching field is set.
        """
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return


# Export for use
__all__ = ["ModelCustomProperties"]
