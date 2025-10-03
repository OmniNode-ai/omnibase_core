"""
Generic Field Converter Pattern.

Provides a reusable, extensible pattern for converting string-based data
to typed fields, replacing large conditional logic with a strategy pattern.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

from omnibase_core.errors.error_codes import CoreErrorCode, OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# Use ModelSchemaValue directly for ONEX compliance

T = TypeVar("T")


@dataclass(frozen=True)
class FieldConverter(Generic[T]):
    """
    Represents a field conversion strategy.

    This replaces hardcoded if/elif chains with a declarative,
    extensible converter registry pattern.
    """

    field_name: str
    converter: Callable[[str], T]
    default_value: T | None = None
    validator: Callable[[T], bool] | None = None

    def convert(self, value: str) -> T:
        """
        Convert string value to typed value.

        Args:
            value: String value to convert

        Returns:
            Converted typed value

        Raises:
            OnexError: If conversion fails
        """
        try:
            result = self.converter(value)

            # Validate if validator provided
            if self.validator and not self.validator(result):
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Validation failed for field {self.field_name}",
                    details=ModelErrorContext.with_context(
                        {
                            "field_name": ModelSchemaValue.from_value(self.field_name),
                            "value": ModelSchemaValue.from_value(value),
                            "converted_value": ModelSchemaValue.from_value(str(result)),
                        },
                    ),
                )

            return result
        except Exception as e:
            if isinstance(e, OnexError):
                raise

            # Use default if available
            if self.default_value is not None:
                return self.default_value

            raise OnexError(
                code=CoreErrorCode.CONVERSION_ERROR,
                message=f"Failed to convert field {self.field_name}: {e!s}",
                details=ModelErrorContext.with_context(
                    {
                        "field_name": ModelSchemaValue.from_value(self.field_name),
                        "value": ModelSchemaValue.from_value(value),
                        "error": ModelSchemaValue.from_value(str(e)),
                    },
                ),
            )


class ModelFieldConverterRegistry:
    """
    Registry for field converters that replaces large conditional logic.

    This pattern eliminates the need for large if/elif chains or
    switch-like patterns when converting string data to typed fields.
    """

    def __init__(self) -> None:
        """Initialize empty converter registry."""
        self._converters: dict[str, FieldConverter[object]] = {}

    def register_boolean_field(
        self,
        field_name: str,
        true_values: set[str] | None = None,
        default: bool | None = None,
    ) -> None:
        """Register a boolean field converter."""
        if true_values is None:
            true_values = {"true", "1", "yes", "on"}

        def str_to_bool(value: str) -> bool:
            return value.lower() in true_values

        self._converters[field_name] = FieldConverter(
            field_name=field_name,
            converter=str_to_bool,
            default_value=default,
        )

    def register_integer_field(
        self,
        field_name: str,
        default: int | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
    ) -> None:
        """Register an integer field converter."""

        def str_to_int(value: str) -> object:
            return int(value)

        def validate_int(value: object) -> bool:
            if not isinstance(value, int):
                return False
            if min_value is not None and value < min_value:
                return False
            if max_value is not None and value > max_value:
                return False
            return True

        self._converters[field_name] = FieldConverter[object](
            field_name=field_name,
            converter=str_to_int,
            default_value=default,
            validator=(
                validate_int
                if (min_value is not None or max_value is not None)
                else None
            ),
        )

    def register_enum_field(
        self,
        field_name: str,
        enum_class: type[Enum],
        default: Enum | None = None,
    ) -> None:
        """Register an enum field converter."""

        def str_to_enum(value: str) -> Enum:
            # Try direct value match first
            for enum_value in enum_class:
                if value == enum_value.value:
                    return enum_value

            # Try case-insensitive name match
            for enum_value in enum_class:
                if value.upper() == enum_value.name.upper():
                    return enum_value

            # Return default or raise error
            if default is not None:
                return default

            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid {enum_class.__name__} value: {value}",
                details=ModelErrorContext.with_context(
                    {
                        "enum_class": ModelSchemaValue.from_value(enum_class.__name__),
                        "invalid_value": ModelSchemaValue.from_value(value),
                        "field_name": ModelSchemaValue.from_value(field_name),
                    },
                ),
            )

        self._converters[field_name] = FieldConverter(
            field_name=field_name,
            converter=str_to_enum,
            default_value=default,
        )

    def register_optional_integer_field(
        self,
        field_name: str,
        zero_as_none: bool = True,
    ) -> None:
        """Register an optional integer field converter."""

        def str_to_optional_int(value: str) -> int | None:
            if not value:
                return None
            int_val = int(value)
            if zero_as_none and int_val == 0:
                return None
            return int_val

        self._converters[field_name] = FieldConverter(
            field_name=field_name,
            converter=str_to_optional_int,
            default_value=None,
        )

    def register_custom_field(
        self,
        field_name: str,
        converter: Callable[[str], object],
        default: object | None = None,
        validator: Callable[[object], bool] | None = None,
    ) -> None:
        """Register a custom field converter."""
        self._converters[field_name] = FieldConverter[object](
            field_name=field_name,
            converter=converter,
            default_value=default,
            validator=validator,
        )

    def convert_field(self, field_name: str, value: str) -> object:
        """
        Convert a field value using registered converter.

        Args:
            field_name: Name of field to convert
            value: String value to convert

        Returns:
            Converted typed value

        Raises:
            OnexError: If no converter registered or conversion fails
        """
        if field_name not in self._converters:
            raise OnexError(
                code=CoreErrorCode.NOT_FOUND,
                message=f"No converter registered for field: {field_name}",
                details=ModelErrorContext.with_context(
                    {
                        "field_name": ModelSchemaValue.from_value(field_name),
                        "available_fields": ModelSchemaValue.from_value(
                            ", ".join(self._converters.keys()),
                        ),
                    },
                ),
            )

        return self._converters[field_name].convert(value)

    def convert_data(self, data: dict[str, str]) -> dict[str, ModelSchemaValue]:
        """
        Convert a dictionary of string data to typed values.

        Args:
            data: Dictionary with string values

        Returns:
            Dictionary with converted typed values (str, int, float, bool)
        """
        result: dict[str, ModelSchemaValue] = {}

        for field_name, value in data.items():
            if field_name in self._converters:
                converted_value = self.convert_field(field_name, value)
                result[field_name] = ModelSchemaValue.from_value(converted_value)
            # Skip unknown fields - let caller handle them

        return result

    def has_converter(self, field_name: str) -> bool:
        """Check if converter is registered for field."""
        return field_name in self._converters

    def list_fields(self) -> list[str]:
        """Get list of registered field names."""
        return list(self._converters.keys())


# Export all types
__all__ = [
    "FieldConverter",
    "ModelFieldConverterRegistry",
]
