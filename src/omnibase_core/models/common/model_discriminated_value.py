"""
ModelDiscriminatedValue

Universal discriminated union for primitive and complex types.

Replaces Union[bool, float, int, str] and Union[bool, dict, float, int, list, str]
patterns with structured type safety and runtime type validation.

This model provides:
- Type-safe value storage with discriminator field
- Runtime type validation
- Metadata support for extensibility
- Helper methods for type checking and value retrieval
- Full Pydantic V2 compliance

Usage Examples:
    # Create from specific type
    value = ModelDiscriminatedValue.from_int(42, metadata={"source": "api"})

    # Create with auto-detection
    value = ModelDiscriminatedValue.from_any("test")

    # Retrieve value
    actual_value = value.get_value()  # Returns 42

    # Type checking
    if value.is_type(int):
        print("It's an integer!")

    # Get Python type
    python_type = value.get_type()  # Returns <class 'int'>

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.enums
- omnibase_core.errors
"""

from __future__ import annotations

import json

# no typing imports needed
from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_discriminated_value_type import EnumDiscriminatedValueType
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelDiscriminatedValue(BaseModel):
    """
    Universal discriminated union for primitive and complex types.

    Provides type-safe alternative to Union[bool, float, int, str] and
    Union[bool, dict, float, int, list, str] patterns.

    The discriminator field (value_type) enables runtime type identification
    and validation, ensuring type safety throughout the system.

    Attributes:
        value_type: Type discriminator (bool, float, int, str, dict, list)
        bool_value: Boolean value (set when value_type is BOOL)
        float_value: Float value (set when value_type is FLOAT)
        int_value: Integer value (set when value_type is INT)
        str_value: String value (set when value_type is STR)
        dict_value: Dictionary value (set when value_type is DICT)
        list_value: List value (set when value_type is LIST)
        metadata: Optional metadata for extensibility

    Examples:
        >>> # Primitive types
        >>> value = ModelDiscriminatedValue.from_bool(True)
        >>> value.get_value()
        True

        >>> # Complex types
        >>> value = ModelDiscriminatedValue.from_dict({"key": "value"})
        >>> value.is_type(dict)
        True

        >>> # Auto-detection
        >>> value = ModelDiscriminatedValue.from_any(42)
        >>> value.get_type()
        <class 'int'>
    """

    value_type: EnumDiscriminatedValueType = Field(
        description="Type discriminator for runtime type identification",
    )

    # Value storage (only one should be populated based on value_type)
    bool_value: bool | None = Field(
        default=None,
        description="Boolean value (set when value_type is BOOL)",
    )
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
        description="String value (set when value_type is STR)",
    )
    dict_value: dict[str, object] | None = Field(
        default=None,
        description="Dictionary value (set when value_type is DICT) - must be JSON-serializable",
    )
    list_value: list[object] | None = Field(
        default=None,
        description="List value (set when value_type is LIST) - must be JSON-serializable",
    )

    # Metadata
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Optional metadata for extensibility",
    )

    @model_validator(mode="after")
    def validate_single_value(self) -> ModelDiscriminatedValue:
        """
        Ensure only one value is set based on type discriminator.

        Validates that exactly one value field is populated and matches
        the value_type discriminator.

        Returns:
            ModelDiscriminatedValue: Validated instance

        Raises:
            ModelOnexError: If validation fails (multiple values set or wrong value)
        """
        values_map = {
            EnumDiscriminatedValueType.BOOL: self.bool_value,
            EnumDiscriminatedValueType.FLOAT: self.float_value,
            EnumDiscriminatedValueType.INT: self.int_value,
            EnumDiscriminatedValueType.STR: self.str_value,
            EnumDiscriminatedValueType.DICT: self.dict_value,
            EnumDiscriminatedValueType.LIST: self.list_value,
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

        # Additional validation for specific types
        if self.value_type == EnumDiscriminatedValueType.DICT and self.dict_value:
            # Validate dict is JSON serializable
            try:
                json.dumps(self.dict_value)
            except (TypeError, ValueError) as e:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Dictionary value is not JSON serializable: {e}",
                ) from e

        if self.value_type == EnumDiscriminatedValueType.LIST and self.list_value:
            # Validate list is JSON serializable
            try:
                json.dumps(self.list_value)
            except (TypeError, ValueError) as e:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"List value is not JSON serializable: {e}",
                ) from e

        return self

    # === Factory Methods ===

    @classmethod
    def from_bool(
        cls, value: bool, metadata: dict[str, str] | None = None
    ) -> ModelDiscriminatedValue:
        """
        Create discriminated value from boolean.

        Args:
            value: Boolean value
            metadata: Optional metadata dict

        Returns:
            ModelDiscriminatedValue: Instance with bool value

        Examples:
            >>> value = ModelDiscriminatedValue.from_bool(True)
            >>> value.get_value()
            True
        """
        return cls(
            value_type=EnumDiscriminatedValueType.BOOL,
            bool_value=value,
            metadata=metadata or {},
        )

    @classmethod
    def from_float(
        cls, value: float, metadata: dict[str, str] | None = None
    ) -> ModelDiscriminatedValue:
        """
        Create discriminated value from float.

        Args:
            value: Float value
            metadata: Optional metadata dict

        Returns:
            ModelDiscriminatedValue: Instance with float value

        Examples:
            >>> value = ModelDiscriminatedValue.from_float(3.14)
            >>> value.get_value()
            3.14
        """
        return cls(
            value_type=EnumDiscriminatedValueType.FLOAT,
            float_value=value,
            metadata=metadata or {},
        )

    @classmethod
    def from_int(
        cls, value: int, metadata: dict[str, str] | None = None
    ) -> ModelDiscriminatedValue:
        """
        Create discriminated value from integer.

        Args:
            value: Integer value
            metadata: Optional metadata dict

        Returns:
            ModelDiscriminatedValue: Instance with int value

        Examples:
            >>> value = ModelDiscriminatedValue.from_int(42)
            >>> value.get_value()
            42
        """
        return cls(
            value_type=EnumDiscriminatedValueType.INT,
            int_value=value,
            metadata=metadata or {},
        )

    @classmethod
    def from_str(
        cls, value: str, metadata: dict[str, str] | None = None
    ) -> ModelDiscriminatedValue:
        """
        Create discriminated value from string.

        Args:
            value: String value
            metadata: Optional metadata dict

        Returns:
            ModelDiscriminatedValue: Instance with str value

        Examples:
            >>> value = ModelDiscriminatedValue.from_str("test")
            >>> value.get_value()
            'test'
        """
        return cls(
            value_type=EnumDiscriminatedValueType.STR,
            str_value=value,
            metadata=metadata or {},
        )

    @classmethod
    def from_dict(
        cls, value: dict[str, object], metadata: dict[str, str] | None = None
    ) -> ModelDiscriminatedValue:
        """
        Create discriminated value from dictionary.

        Args:
            value: Dictionary value (must be JSON serializable)
            metadata: Optional metadata dict

        Returns:
            ModelDiscriminatedValue: Instance with dict value

        Raises:
            ModelOnexError: If dict is not JSON serializable

        Examples:
            >>> value = ModelDiscriminatedValue.from_dict({"key": "value"})
            >>> value.get_value()
            {'key': 'value'}
        """
        return cls(
            value_type=EnumDiscriminatedValueType.DICT,
            dict_value=value,
            metadata=metadata or {},
        )

    @classmethod
    def from_list(
        cls, value: list[object], metadata: dict[str, str] | None = None
    ) -> ModelDiscriminatedValue:
        """
        Create discriminated value from list.

        Args:
            value: List value (must be JSON serializable)
            metadata: Optional metadata dict

        Returns:
            ModelDiscriminatedValue: Instance with list value

        Raises:
            ModelOnexError: If list is not JSON serializable

        Examples:
            >>> value = ModelDiscriminatedValue.from_list([1, 2, 3])
            >>> value.get_value()
            [1, 2, 3]
        """
        return cls(
            value_type=EnumDiscriminatedValueType.LIST,
            list_value=value,
            metadata=metadata or {},
        )

    @classmethod
    def from_any(
        cls,
        # union-ok: discriminated_union - factory creates discriminated value with EnumDiscriminatedValueType
        value: bool | float | int | str | dict[str, object] | list[object],
        metadata: dict[str, str] | None = None,
    ) -> ModelDiscriminatedValue:
        """
        Create discriminated value with automatic type detection.

        Detects the type of the value and creates appropriate discriminated value.
        Note: bool must be checked before int since bool is a subclass of int.

        Args:
            value: Value of any supported type
            metadata: Optional metadata dict

        Returns:
            ModelDiscriminatedValue: Instance with detected type

        Examples:
            >>> ModelDiscriminatedValue.from_any(42).get_type()
            <class 'int'>
            >>> ModelDiscriminatedValue.from_any("test").get_type()
            <class 'str'>
            >>> ModelDiscriminatedValue.from_any(True).get_type()
            <class 'bool'>
        """
        # Check bool before int (bool is subclass of int)
        if isinstance(value, bool):
            return cls.from_bool(value, metadata)
        if isinstance(value, int):
            return cls.from_int(value, metadata)
        if isinstance(value, float):
            return cls.from_float(value, metadata)
        if isinstance(value, str):
            return cls.from_str(value, metadata)
        if isinstance(value, dict):
            return cls.from_dict(value, metadata)
        if isinstance(value, list):
            return cls.from_list(value, metadata)

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unsupported type for discriminated value: {type(value)}",
            context={"value_type": str(type(value))},
        )

    # === Helper Methods ===

    # union-ok: discriminated_union - return type matches discriminated value storage fields
    def get_value(self) -> bool | float | int | str | dict[str, object] | list[object]:
        """
        Get the actual value with proper type.

        Returns:
            The stored value with correct type

        Examples:
            >>> value = ModelDiscriminatedValue.from_int(42)
            >>> value.get_value()
            42
        """
        if self.value_type == EnumDiscriminatedValueType.BOOL:
            # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
            return self.bool_value  # type: ignore[return-value]
        if self.value_type == EnumDiscriminatedValueType.FLOAT:
            # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
            return self.float_value  # type: ignore[return-value]
        if self.value_type == EnumDiscriminatedValueType.INT:
            # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
            return self.int_value  # type: ignore[return-value]
        if self.value_type == EnumDiscriminatedValueType.STR:
            # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
            return self.str_value  # type: ignore[return-value]
        if self.value_type == EnumDiscriminatedValueType.DICT:
            # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
            return self.dict_value  # type: ignore[return-value]
        if self.value_type == EnumDiscriminatedValueType.LIST:
            # NOTE(OMN-1302): Value guaranteed non-None by value_type discriminator check and model validator.
            return self.list_value  # type: ignore[return-value]

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
            >>> value = ModelDiscriminatedValue.from_int(42)
            >>> value.get_type()
            <class 'int'>
        """
        type_map = {
            EnumDiscriminatedValueType.BOOL: bool,
            EnumDiscriminatedValueType.FLOAT: float,
            EnumDiscriminatedValueType.INT: int,
            EnumDiscriminatedValueType.STR: str,
            EnumDiscriminatedValueType.DICT: dict,
            EnumDiscriminatedValueType.LIST: list,
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
            >>> value = ModelDiscriminatedValue.from_int(42)
            >>> value.is_type(int)
            True
            >>> value.is_type(str)
            False
        """
        return self.get_type() == expected_type

    def is_primitive(self) -> bool:
        """
        Check if the value is a primitive type.

        Returns:
            bool: True if value is bool, float, int, or str

        Examples:
            >>> ModelDiscriminatedValue.from_int(42).is_primitive()
            True
            >>> ModelDiscriminatedValue.from_list([1, 2]).is_primitive()
            False
        """
        return EnumDiscriminatedValueType.is_primitive_type(self.value_type)

    def is_numeric(self) -> bool:
        """
        Check if the value is numeric.

        Returns:
            bool: True if value is int or float

        Examples:
            >>> ModelDiscriminatedValue.from_int(42).is_numeric()
            True
            >>> ModelDiscriminatedValue.from_str("test").is_numeric()
            False
        """
        return EnumDiscriminatedValueType.is_numeric_type(self.value_type)

    def is_collection(self) -> bool:
        """
        Check if the value is a collection.

        Returns:
            bool: True if value is dict or list

        Examples:
            >>> ModelDiscriminatedValue.from_list([1, 2]).is_collection()
            True
            >>> ModelDiscriminatedValue.from_int(42).is_collection()
            False
        """
        return EnumDiscriminatedValueType.is_collection_type(self.value_type)

    def __eq__(self, other: object) -> bool:
        """
        Equality comparison.

        Args:
            other: Object to compare with

        Returns:
            bool: True if values are equal
        """
        if isinstance(other, ModelDiscriminatedValue):
            return (
                self.value_type == other.value_type
                and self.get_value() == other.get_value()
            )
        return bool(self.get_value() == other)

    def __str__(self) -> str:
        """String representation."""
        value = self.get_value()
        return f"DiscriminatedValue({self.value_type}: {value})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"ModelDiscriminatedValue(value_type='{self.value_type}', "
            f"value={self.get_value()!r})"
        )

    model_config = ConfigDict(
        extra="ignore",
        frozen=False,
        use_enum_values=False,
        validate_assignment=True,
    )


# Export for use
__all__ = ["ModelDiscriminatedValue"]
