"""
ModelMultiTypeValue

Type-safe wrapper for common primitive value unions without dict support.

This model provides automatic type inference and validation for union types,
replacing bare Union[bool, float, int, list, str] patterns with structured
type safety.

Features:
- Automatic type inference from value
- Type consistency validation WITHOUT coercion (bool does not coerce to int)
- Support for primitives: bool, int, float, str
- Support for collections: list[Any]
- Comprehensive validation with detailed error messages
- Full mypy strict mode compliance

Usage Examples:
    # Automatic type inference
    >>> value = ModelMultiTypeValue(value=42)
    >>> assert value.value_type == "int"
    >>> assert value.get_value() == 42

    # Explicit type specification
    >>> value = ModelMultiTypeValue(value="hello", value_type="str")
    >>> assert value.value_type == "str"

    # Type checking
    >>> value = ModelMultiTypeValue(value=True)
    >>> assert value.is_type(bool) is True
    >>> assert value.get_python_type() == bool

Security Features:
- Maximum list size limit to prevent DoS attacks
- String length validation
- NaN and infinity detection for float values

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.errors modules
- pydantic modules
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelMultiTypeValue(BaseModel):
    """
    Type-safe wrapper for common primitive value unions without dict support.

    Replaces bare Union[bool, float, int, list, str] patterns with structured,
    validated union types that preserve type information.

    The model automatically infers the type from the provided value
    when value_type is not explicitly specified.

    Attributes:
        value: The actual value (bool, int, float, str, or list)
        value_type: Type discriminator ("bool", "int", "float", "str", "list")
        metadata: Optional metadata for the value (string-to-string mapping)

    Examples:
        # Automatic type inference
        >>> value = ModelMultiTypeValue(value=42)
        >>> assert value.value_type == "int"

        # Explicit type
        >>> value = ModelMultiTypeValue(value="hello", value_type="str")
        >>> assert value.value_type == "str"

        # Complex types
        >>> value = ModelMultiTypeValue(value=[1, 2, 3])
        >>> assert value.value_type == "list"

        # Boolean distinction (NOT coerced to int)
        >>> value = ModelMultiTypeValue(value=True)
        >>> assert value.value_type == "bool"
        >>> assert value.is_type(bool) is True
    """

    # Security constants - prevent DoS via large collections
    MAX_LIST_SIZE: int = 10000
    MAX_STRING_LENGTH: int = 1000000  # 1MB character limit

    # union-ok: discriminated_union - companion value_type Literal field provides type safety
    value: bool | int | float | str | list[object] = Field(
        description="The actual value",
    )

    value_type: Literal["bool", "int", "float", "str", "list"] = Field(
        description="Type discriminator for the value",
    )

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Optional string metadata",
    )

    @model_validator(mode="before")
    @classmethod
    def infer_value_type(cls, data: object) -> dict[str, object]:
        """
        Automatically infer value_type from value if not provided.

        This validator runs before field validation and auto-populates
        the value_type field based on the Python type of the value.

        Type inference rules:
        - bool is checked before int (since bool is subclass of int)
        - int, float, str are checked in order
        - list is checked for collections

        Args:
            data: Input data (dict or value)

        Returns:
            dict[str, object]: Data with value_type populated

        Raises:
            ModelOnexError: If value type is unsupported
        """
        # Ensure data is a dict (help mypy with type narrowing)
        data_dict: dict[str, object]
        if not isinstance(data, dict):
            data_dict = {"value": data}
        else:
            data_dict = data

        # If value_type already specified, validate it's correct
        if "value_type" in data_dict:
            return data_dict

        # Infer type from value
        value = data_dict.get("value")

        # Check bool BEFORE int (bool is subclass of int in Python)
        if isinstance(value, bool):
            data_dict["value_type"] = "bool"
        elif isinstance(value, int):
            data_dict["value_type"] = "int"
        elif isinstance(value, float):
            data_dict["value_type"] = "float"
        elif isinstance(value, str):
            data_dict["value_type"] = "str"
        elif isinstance(value, list):
            data_dict["value_type"] = "list"
        else:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unsupported value type: {type(value).__name__}",
                context={
                    "value_type": type(value).__name__,
                    "supported_types": "bool, int, float, str, list",
                },
            )

        return data_dict

    @model_validator(mode="after")
    def validate_value_type_match(self) -> ModelMultiTypeValue:
        """
        Validate that value matches the declared value_type.

        This validator runs after field validation and ensures type consistency
        between the value and value_type fields.

        Special handling:
        - bool is checked before int (bool is subclass of int)
        - float NaN and infinity values are detected and rejected
        - Empty strings are allowed
        - Empty collections are allowed

        Returns:
            ModelMultiTypeValue: Self if validation passes

        Raises:
            ModelOnexError: If value doesn't match declared type
        """
        # Type checking map - note bool must be checked before int
        type_checks = {
            "bool": lambda x: isinstance(x, bool),
            "int": lambda x: isinstance(x, int) and not isinstance(x, bool),
            "float": lambda x: isinstance(x, float),
            "str": lambda x: isinstance(x, str),
            "list": lambda x: isinstance(x, list),
        }

        # Validate type consistency
        type_check = type_checks.get(self.value_type)
        if type_check is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unknown value_type: {self.value_type}",
                context={
                    "value_type": self.value_type,
                    "allowed_types": "bool, int, float, str, list",
                },
            )

        if not type_check(self.value):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value type mismatch: expected {self.value_type}, got {type(self.value).__name__}",
                context={
                    "expected_type": self.value_type,
                    "actual_type": type(self.value).__name__,
                    "value": str(self.value),
                },
            )

        # Type-specific validation with type narrowing for mypy
        if self.value_type == "float":
            # Type narrowing: at this point we know value is float
            if isinstance(self.value, float):
                # Reject NaN and infinity
                if math.isnan(self.value) or math.isinf(self.value):
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message="Float value cannot be NaN or infinity",
                        context={
                            "value": str(self.value),
                            "is_nan": math.isnan(self.value),
                            "is_inf": math.isinf(self.value),
                        },
                    )

        elif self.value_type == "str":
            # Type narrowing: at this point we know value is str
            if isinstance(self.value, str):
                # Check string length for DoS prevention
                if len(self.value) > self.MAX_STRING_LENGTH:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"String exceeds maximum length of {self.MAX_STRING_LENGTH}",
                        context={
                            "string_length": len(self.value),
                            "max_length": self.MAX_STRING_LENGTH,
                        },
                    )

        elif self.value_type == "list":
            # Type narrowing: at this point we know value is list
            if isinstance(self.value, list):
                # Check list size for DoS prevention
                if len(self.value) > self.MAX_LIST_SIZE:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"List exceeds maximum size of {self.MAX_LIST_SIZE}",
                        context={
                            "list_size": len(self.value),
                            "max_size": self.MAX_LIST_SIZE,
                        },
                    )

        return self

    # union-ok: discriminated_union - return type matches discriminated value field
    def get_value(self) -> bool | int | float | str | list[object]:
        """
        Get the stored value with proper type.

        Returns:
            The actual value with its native Python type

        Examples:
            >>> value = ModelMultiTypeValue(value=42)
            >>> assert value.get_value() == 42
            >>> assert isinstance(value.get_value(), int)
        """
        return self.value

    def get_python_type(self) -> type:
        """
        Get the Python type of the stored value.

        Returns:
            type: The Python type class (bool, int, float, str, list)

        Examples:
            >>> value = ModelMultiTypeValue(value="hello")
            >>> assert value.get_python_type() == str
        """
        type_map = {
            "bool": bool,
            "int": int,
            "float": float,
            "str": str,
            "list": list,
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
            >>> value = ModelMultiTypeValue(value=42)
            >>> assert value.is_type(int) is True
            >>> assert value.is_type(str) is False
        """
        return self.get_python_type() == expected_type

    def as_dict(self) -> dict[str, object]:
        """
        Convert to dictionary representation.

        Returns:
            dict[str, object]: Dictionary with value, value_type, and metadata

        Examples:
            >>> value = ModelMultiTypeValue(value=42)
            >>> data = value.as_dict()
            >>> assert data["value"] == 42
            >>> assert data["value_type"] == "int"
        """
        return {
            "value": self.value,
            "value_type": self.value_type,
            "metadata": self.metadata,
        }

    def is_primitive(self) -> bool:
        """
        Check if value is a primitive type (bool, int, float, str).

        Returns:
            bool: True if value is primitive, False if collection

        Examples:
            >>> value = ModelMultiTypeValue(value=42)
            >>> assert value.is_primitive() is True
            >>> value = ModelMultiTypeValue(value=[1, 2, 3])
            >>> assert value.is_primitive() is False
        """
        return self.value_type in ("bool", "int", "float", "str")

    def is_collection(self) -> bool:
        """
        Check if value is a collection type (list).

        Returns:
            bool: True if value is collection, False if primitive

        Examples:
            >>> value = ModelMultiTypeValue(value=[1, 2, 3])
            >>> assert value.is_collection() is True
            >>> value = ModelMultiTypeValue(value=42)
            >>> assert value.is_collection() is False
        """
        return self.value_type == "list"

    def __str__(self) -> str:
        """String representation."""
        return f"MultiTypeValue({self.value_type}: {self.value})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"ModelMultiTypeValue(value_type='{self.value_type}', value={self.value!r})"
        )

    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
    )


__all__ = ["ModelMultiTypeValue"]
