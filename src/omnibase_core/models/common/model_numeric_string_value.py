"""
ModelNumericStringValue

Type-safe numeric value with string fallback support.

Replaces Union[float, int, str] patterns with structured type safety
and runtime type validation, specifically designed for configuration
values and environment variables that can be numeric or string.

This model provides:
- Type-safe value storage with discriminator field
- Numeric coercion with configurable modes
- String parsing with validation
- Helper methods for type checking and value retrieval
- Full Pydantic V2 compliance

Usage Examples:
    # Create from specific type
    value = ModelNumericStringValue.from_int(42, metadata={"source": "config"})

    # Create with auto-detection
    value = ModelNumericStringValue.from_any(3.14)

    # Retrieve as different types with coercion
    as_int = value.get_as_int(coercion_mode=EnumCoercionMode.ROUND)
    as_float = value.get_as_float()
    as_str = value.get_as_str()

    # Type checking
    if value.is_numeric():
        print("It's a number!")

    # String parsing
    value = ModelNumericStringValue.from_str("123")
    assert value.get_as_int() == 123

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.enums
- omnibase_core.errors
- omnibase_core.models.common.model_coercion_mode
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_numeric_value_type import EnumNumericValueType
from omnibase_core.models.common.model_coercion_mode import EnumCoercionMode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = ["ModelNumericStringValue"]


class ModelNumericStringValue(BaseModel):
    """
    Type-safe numeric value with string fallback support.

    Provides type-safe alternative to Union[float, int, str] patterns
    commonly used for configuration values and environment variables.

    The discriminator field (value_type) enables runtime type identification
    and validation, ensuring type safety throughout the system.

    Attributes:
        value_type: Type discriminator (float, int, string)
        float_value: Float value (set when value_type is FLOAT)
        int_value: Integer value (set when value_type is INT)
        str_value: String value (set when value_type is STRING)
        metadata: Optional metadata for extensibility

    Examples:
        >>> # Integer values
        >>> value = ModelNumericStringValue.from_int(42)
        >>> value.get_as_int()
        42

        >>> # Float values
        >>> value = ModelNumericStringValue.from_float(3.14)
        >>> value.get_as_float()
        3.14

        >>> # String values with parsing
        >>> value = ModelNumericStringValue.from_str("123")
        >>> value.get_as_int()
        123

        >>> # Auto-detection
        >>> value = ModelNumericStringValue.from_any(42)
        >>> value.get_type()
        <class 'int'>
    """

    value_type: EnumNumericValueType = Field(
        description="Type discriminator for runtime type identification",
    )

    # Value storage (only one should be populated based on value_type)
    float_value: float | None = Field(
        default=None,
        description="Float value (set when value_type is FLOAT)",
    )
    int_value: int | None = Field(
        default=None,
        description="Integer value (set when value_type is INT)",
    )
    str_value: str | None = Field(
        default=None,
        description="String value (set when value_type is STRING)",
    )

    # Metadata
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Optional metadata for extensibility",
    )

    @model_validator(mode="after")
    def validate_single_value(self) -> ModelNumericStringValue:
        """
        Ensure only one value is set based on type discriminator.

        Validates that exactly one value field is populated and matches
        the value_type discriminator.

        Returns:
            ModelNumericStringValue: Validated instance

        Raises:
            ModelOnexError: If validation fails (multiple values set or wrong value)
        """
        values_map = {
            EnumNumericValueType.FLOAT: self.float_value,
            EnumNumericValueType.INT: self.int_value,
            EnumNumericValueType.STRING: self.str_value,
        }

        # Count non-None values
        non_none_count = sum(1 for v in values_map.values() if v is not None)

        # Exactly one value should be set
        if non_none_count != 1:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Exactly one value must be set for value_type '{self.value_type}'",
                context={
                    "value_type": str(self.value_type),
                    "non_none_count": non_none_count,
                },
            )

        # Validate that the correct value is set for the type
        expected_value = values_map[self.value_type]
        if expected_value is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Required value for type '{self.value_type}' is None",
                context={
                    "value_type": str(self.value_type),
                    "required_field": f"{self.value_type}_value",
                },
            )

        # Additional validation for float values
        if (
            self.value_type == EnumNumericValueType.FLOAT
            and self.float_value is not None
        ):
            if math.isnan(self.float_value) or math.isinf(self.float_value):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Float value cannot be NaN or infinity",
                    context={
                        "value": str(self.float_value),
                        "is_nan": math.isnan(self.float_value),
                        "is_inf": math.isinf(self.float_value),
                    },
                )

        return self

    # === Factory Methods ===

    @classmethod
    def from_float(
        cls, value: float, metadata: dict[str, str] | None = None
    ) -> ModelNumericStringValue:
        """
        Create numeric value from float.

        Args:
            value: Float value
            metadata: Optional metadata dict

        Returns:
            ModelNumericStringValue: Instance with float value

        Raises:
            ModelOnexError: If value is NaN or infinity

        Examples:
            >>> value = ModelNumericStringValue.from_float(3.14)
            >>> value.get_as_float()
            3.14
        """
        return cls(
            value_type=EnumNumericValueType.FLOAT,
            float_value=value,
            metadata=metadata or {},
        )

    @classmethod
    def from_int(
        cls, value: int, metadata: dict[str, str] | None = None
    ) -> ModelNumericStringValue:
        """
        Create numeric value from integer.

        Args:
            value: Integer value
            metadata: Optional metadata dict

        Returns:
            ModelNumericStringValue: Instance with int value

        Examples:
            >>> value = ModelNumericStringValue.from_int(42)
            >>> value.get_as_int()
            42
        """
        return cls(
            value_type=EnumNumericValueType.INT,
            int_value=value,
            metadata=metadata or {},
        )

    @classmethod
    def from_str(
        cls, value: str, metadata: dict[str, str] | None = None
    ) -> ModelNumericStringValue:
        """
        Create numeric value from string.

        Args:
            value: String value
            metadata: Optional metadata dict

        Returns:
            ModelNumericStringValue: Instance with str value

        Examples:
            >>> value = ModelNumericStringValue.from_str("test")
            >>> value.get_as_str()
            'test'

            >>> value = ModelNumericStringValue.from_str("123")
            >>> value.get_as_int()
            123
        """
        return cls(
            value_type=EnumNumericValueType.STRING,
            str_value=value,
            metadata=metadata or {},
        )

    @classmethod
    def from_any(
        cls,
        value: float | int | str,
        metadata: dict[str, str] | None = None,
    ) -> ModelNumericStringValue:
        """
        Create numeric value with automatic type detection.

        Detects the type of the value and creates appropriate numeric value.
        Note: Checks int before float to maintain proper type discrimination.

        Args:
            value: Value of any supported type
            metadata: Optional metadata dict

        Returns:
            ModelNumericStringValue: Instance with detected type

        Examples:
            >>> ModelNumericStringValue.from_any(42).get_type()
            <class 'int'>
            >>> ModelNumericStringValue.from_any(3.14).get_type()
            <class 'float'>
            >>> ModelNumericStringValue.from_any("test").get_type()
            <class 'str'>
        """
        # Check int before float (more specific type)
        if isinstance(value, bool):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Boolean values not supported for numeric value (use int explicitly: 0 or 1)",
                context={"value": str(value), "value_type": "bool"},
            )
        if isinstance(value, int):
            return cls.from_int(value, metadata)
        if isinstance(value, float):
            return cls.from_float(value, metadata)
        if isinstance(value, str):
            return cls.from_str(value, metadata)

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unsupported type for numeric value: {type(value)}",
            context={"value_type": str(type(value))},
        )

    # === Conversion Methods ===

    def get_as_float(self) -> float:
        """
        Get the value as a float with automatic coercion.

        Converts int and parseable strings to float.

        Returns:
            float: The value as float

        Raises:
            ModelOnexError: If string cannot be parsed as float

        Examples:
            >>> ModelNumericStringValue.from_float(3.14).get_as_float()
            3.14
            >>> ModelNumericStringValue.from_int(42).get_as_float()
            42.0
            >>> ModelNumericStringValue.from_str("3.14").get_as_float()
            3.14
        """
        if self.value_type == EnumNumericValueType.FLOAT:
            # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
            return self.float_value  # type: ignore[return-value]
        if self.value_type == EnumNumericValueType.INT:
            # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
            return float(self.int_value)  # type: ignore[arg-type]
        if self.value_type == EnumNumericValueType.STRING:
            try:
                # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
                return float(self.str_value)  # type: ignore[arg-type]
            except (TypeError, ValueError) as e:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Cannot convert string '{self.str_value}' to float",
                    context={
                        "string_value": str(self.str_value),
                        "error": str(e),
                    },
                ) from e

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unknown value_type: {self.value_type}",
            context={"value_type": str(self.value_type)},
        )

    def get_as_int(
        self, coercion_mode: EnumCoercionMode = EnumCoercionMode.STRICT
    ) -> int:
        """
        Get the value as an integer with configurable coercion.

        Converts float and parseable strings to int based on coercion mode.

        Args:
            coercion_mode: How to convert float to int (STRICT, FLOOR, CEIL, ROUND)

        Returns:
            int: The value as integer

        Raises:
            ModelOnexError: If conversion fails or coercion mode is invalid

        Examples:
            >>> ModelNumericStringValue.from_int(42).get_as_int()
            42
            >>> ModelNumericStringValue.from_float(3.0).get_as_int()
            3
            >>> ModelNumericStringValue.from_float(3.7).get_as_int(EnumCoercionMode.ROUND)
            4
            >>> ModelNumericStringValue.from_str("123").get_as_int()
            123
        """
        if self.value_type == EnumNumericValueType.INT:
            # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
            return self.int_value  # type: ignore[return-value]

        if self.value_type == EnumNumericValueType.FLOAT:
            float_val = self.float_value
            # Type guard: float_value should not be None if value_type is FLOAT
            if float_val is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Float value is None but value_type is FLOAT",
                    context={"value_type": str(self.value_type)},
                )

            # Apply coercion based on mode
            if coercion_mode == EnumCoercionMode.STRICT:
                # Only exact floats allowed (e.g., 3.0)
                if float_val != int(float_val):
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Float value {float_val} is not an exact integer (use FLOOR, CEIL, or ROUND mode)",
                        context={
                            "value": str(float_val),
                            "coercion_mode": "strict",
                            "fractional_part": str(float_val - int(float_val)),
                        },
                    )
                return int(float_val)

            elif coercion_mode == EnumCoercionMode.FLOOR:
                return math.floor(float_val)

            elif coercion_mode == EnumCoercionMode.CEIL:
                return math.ceil(float_val)

            elif coercion_mode == EnumCoercionMode.ROUND:
                return round(float_val)

            else:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Unknown coercion mode: {coercion_mode}",
                    context={"coercion_mode": str(coercion_mode)},
                )

        if self.value_type == EnumNumericValueType.STRING:
            try:
                # Try direct int conversion first
                # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
                return int(self.str_value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                # Try parsing as float first, then convert to int
                try:
                    # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
                    float_val = float(self.str_value)  # type: ignore[arg-type]
                    # Apply coercion mode to the parsed float
                    if coercion_mode == EnumCoercionMode.STRICT:
                        if float_val != int(float_val):
                            raise ModelOnexError(
                                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                                message=f"String '{self.str_value}' parses to non-exact float {float_val}",
                                context={
                                    "string_value": str(self.str_value),
                                    "parsed_float": str(float_val),
                                    "coercion_mode": "strict",
                                },
                            )
                        return int(float_val)
                    elif coercion_mode == EnumCoercionMode.FLOOR:
                        return math.floor(float_val)
                    elif coercion_mode == EnumCoercionMode.CEIL:
                        return math.ceil(float_val)
                    elif coercion_mode == EnumCoercionMode.ROUND:
                        return round(float_val)
                except (OverflowError, TypeError, ValueError) as e:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Cannot convert string '{self.str_value}' to int",
                        context={
                            "string_value": str(self.str_value),
                            "error": str(e),
                        },
                    ) from e

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unknown value_type: {self.value_type}",
            context={"value_type": str(self.value_type)},
        )

    def get_as_str(self) -> str:
        """
        Get the value as a string.

        Always succeeds - converts numeric values to their string representation.

        Returns:
            str: The value as string

        Examples:
            >>> ModelNumericStringValue.from_str("test").get_as_str()
            'test'
            >>> ModelNumericStringValue.from_int(42).get_as_str()
            '42'
            >>> ModelNumericStringValue.from_float(3.14).get_as_str()
            '3.14'
        """
        if self.value_type == EnumNumericValueType.STRING:
            # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
            return self.str_value  # type: ignore[return-value]
        if self.value_type == EnumNumericValueType.INT:
            return str(self.int_value)
        if self.value_type == EnumNumericValueType.FLOAT:
            return str(self.float_value)

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unknown value_type: {self.value_type}",
            context={"value_type": str(self.value_type)},
        )

    # === Helper Methods ===

    def get_value(self) -> float | int | str:
        """
        Get the actual value with proper type.

        Returns:
            The stored value with correct type

        Examples:
            >>> value = ModelNumericStringValue.from_int(42)
            >>> value.get_value()
            42
        """
        if self.value_type == EnumNumericValueType.FLOAT:
            # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
            return self.float_value  # type: ignore[return-value]
        if self.value_type == EnumNumericValueType.INT:
            # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
            return self.int_value  # type: ignore[return-value]
        if self.value_type == EnumNumericValueType.STRING:
            # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
            return self.str_value  # type: ignore[return-value]

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unknown value_type: {self.value_type}",
            context={"value_type": str(self.value_type)},
        )

    def get_type(self) -> type:
        """
        Get the Python type of the stored value.

        Returns:
            Python type class

        Examples:
            >>> value = ModelNumericStringValue.from_int(42)
            >>> value.get_type()
            <class 'int'>
        """
        type_map = {
            EnumNumericValueType.FLOAT: float,
            EnumNumericValueType.INT: int,
            EnumNumericValueType.STRING: str,
        }
        return type_map[self.value_type]

    def is_type(self, expected_type: type) -> bool:
        """
        Check if the value matches the expected type.

        Args:
            expected_type: Expected Python type

        Returns:
            bool: True if types match

        Examples:
            >>> value = ModelNumericStringValue.from_int(42)
            >>> value.is_type(int)
            True
            >>> value.is_type(str)
            False
        """
        return self.get_type() == expected_type

    def is_float(self) -> bool:
        """
        Check if the value is a float.

        Returns:
            bool: True if value is float

        Examples:
            >>> ModelNumericStringValue.from_float(3.14).is_float()
            True
            >>> ModelNumericStringValue.from_int(42).is_float()
            False
        """
        return self.value_type == EnumNumericValueType.FLOAT

    def is_int(self) -> bool:
        """
        Check if the value is an integer.

        Returns:
            bool: True if value is int

        Examples:
            >>> ModelNumericStringValue.from_int(42).is_int()
            True
            >>> ModelNumericStringValue.from_float(3.14).is_int()
            False
        """
        return self.value_type == EnumNumericValueType.INT

    def is_string(self) -> bool:
        """
        Check if the value is a string.

        Returns:
            bool: True if value is string

        Examples:
            >>> ModelNumericStringValue.from_str("test").is_string()
            True
            >>> ModelNumericStringValue.from_int(42).is_string()
            False
        """
        return self.value_type == EnumNumericValueType.STRING

    def is_numeric(self) -> bool:
        """
        Check if the value is numeric (int or float).

        Returns:
            bool: True if value is int or float

        Examples:
            >>> ModelNumericStringValue.from_int(42).is_numeric()
            True
            >>> ModelNumericStringValue.from_float(3.14).is_numeric()
            True
            >>> ModelNumericStringValue.from_str("test").is_numeric()
            False
        """
        return EnumNumericValueType.is_numeric_type(self.value_type)

    def __eq__(self, other: object) -> bool:
        """
        Equality comparison.

        Args:
            other: Object to compare with

        Returns:
            bool: True if values are equal
        """
        if isinstance(other, ModelNumericStringValue):
            return (
                self.value_type == other.value_type
                and self.get_value() == other.get_value()
            )
        return bool(self.get_value() == other)

    def __str__(self) -> str:
        """String representation."""
        value = self.get_value()
        return f"NumericStringValue({self.value_type}: {value})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"ModelNumericStringValue(value_type='{self.value_type}', "
            f"value={self.get_value()!r})"
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
