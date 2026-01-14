"""ModelValueUnion - Type-safe wrapper for common primitive value unions.

This model provides automatic type inference and validation for union types,
replacing bare Union[bool, float, int, list, str] and
Union[bool, dict, float, int, list, str] patterns with structured type safety.

Features:
    - Automatic type inference from value
    - Type consistency validation
    - Support for nested collections (List[Any], Dict[str, Any])
    - Comprehensive validation with detailed error messages
    - Full mypy strict mode compliance

Usage Examples:
    # Automatic type inference
    >>> value = ModelValueUnion(value=42)
    >>> assert value.value_type == "int"
    >>> assert value.get_value() == 42

    # Explicit type specification
    >>> value = ModelValueUnion(value="hello", value_type="str")
    >>> assert value.value_type == "str"

    # Complex types
    >>> value = ModelValueUnion(value={"key": "value"})
    >>> assert value.value_type == "dict"
    >>> assert value.get_python_type() == dict

Security Features:
    - Maximum list size limit to prevent DoS attacks
    - Maximum dict size limit to prevent DoS attacks
    - String key validation for dict values
    - NaN and infinity detection for float values

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
    - Standard library modules only
    - omnibase_core.enums modules
    - omnibase_core.models.errors modules
    - pydantic modules
"""

from __future__ import annotations

import math
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelValueUnion(BaseModel):
    """
    Type-safe wrapper for common primitive value unions.

    Replaces bare Union[bool, float, int, list, str] and
    Union[bool, dict, float, int, list, str] patterns with structured,
    validated union types that preserve type information.

    The model automatically infers the type from the provided value
    when value_type is not explicitly specified.

    Attributes:
        value: The actual value (bool, int, float, str, list, or dict)
        value_type: Type discriminator ("bool", "int", "float", "str", "list", "dict")
        metadata: Optional metadata for the value (string-to-string mapping)

    Examples:
        # Automatic type inference
        >>> value = ModelValueUnion(value=42)
        >>> assert value.value_type == "int"

        # Explicit type
        >>> value = ModelValueUnion(value="hello", value_type="str")
        >>> assert value.value_type == "str"

        # Complex types
        >>> value = ModelValueUnion(value={"key": "value"})
        >>> assert value.value_type == "dict"
    """

    # Security constants - prevent DoS via large collections
    MAX_LIST_SIZE: ClassVar[int] = 10000
    MAX_DICT_SIZE: ClassVar[int] = 1000

    # union-ok: discriminated_union - companion value_type Literal field provides type safety
    value: bool | int | float | str | list[object] | dict[str, object] = Field(
        description="The actual value",
    )

    value_type: Literal["bool", "int", "float", "str", "list", "dict"] = Field(
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
        - list and dict are checked for collections

        Args:
            data: Input data (dict or value)

        Returns:
            dict[str, object]: Data with value_type populated

        Raises:
            ModelOnexError: If value type is unsupported
        """
        # Ensure data is a dict
        result: dict[str, object]
        if not isinstance(data, dict):
            result = {"value": data}
        else:
            result = data

        # If value_type already specified, validate it's correct
        if "value_type" in result:
            return result

        # Infer type from value
        value = result.get("value")

        # Check bool BEFORE int (bool is subclass of int in Python)
        if isinstance(value, bool):
            result["value_type"] = "bool"
        elif isinstance(value, int):
            result["value_type"] = "int"
        elif isinstance(value, float):
            result["value_type"] = "float"
        elif isinstance(value, str):
            result["value_type"] = "str"
        elif isinstance(value, list):
            result["value_type"] = "list"
        elif isinstance(value, dict):
            result["value_type"] = "dict"
        else:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unsupported value type: {type(value).__name__}",
                context={
                    "value_type": type(value).__name__,
                    "supported_types": "bool, int, float, str, list, dict",
                },
            )

        return result

    @model_validator(mode="after")
    def validate_value_type_match(self) -> ModelValueUnion:
        """
        Validate that value matches the declared value_type.

        This validator runs after field validation and ensures type consistency
        between the value and value_type fields.

        Special handling:
        - bool is checked before int (bool is subclass of int)
        - float NaN and infinity values are detected and rejected
        - Empty strings are allowed
        - Empty collections are allowed
        - Dict keys must be strings for JSON compatibility

        Returns:
            ModelValueUnion: Self if validation passes

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
            "dict": lambda x: isinstance(x, dict),
        }

        # Validate type consistency
        type_check = type_checks.get(self.value_type)
        if type_check is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unknown value_type: {self.value_type}",
                context={
                    "value_type": self.value_type,
                    "allowed_types": "bool, int, float, str, list, dict",
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

        elif self.value_type == "dict":
            # Type narrowing: at this point we know value is dict
            if isinstance(self.value, dict):
                # Check dict size for DoS prevention
                if len(self.value) > self.MAX_DICT_SIZE:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Dict exceeds maximum size of {self.MAX_DICT_SIZE}",
                        context={
                            "dict_size": len(self.value),
                            "max_size": self.MAX_DICT_SIZE,
                        },
                    )

                # Validate all keys are strings for JSON compatibility
                non_string_keys = [k for k in self.value if not isinstance(k, str)]
                if non_string_keys:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message="Dict keys must be strings for JSON compatibility",
                        context={
                            "non_string_keys": str(non_string_keys[:5]),  # Show first 5
                            "non_string_key_count": len(non_string_keys),
                        },
                    )

        return self

    # union-ok: discriminated_union - return type matches discriminated value field
    def get_value(
        self,
    ) -> bool | int | float | str | list[object] | dict[str, object]:
        """
        Get the stored value with proper type.

        Returns:
            The actual value with its native Python type

        Examples:
            >>> value = ModelValueUnion(value=42)
            >>> assert value.get_value() == 42
            >>> assert isinstance(value.get_value(), int)
        """
        return self.value

    def get_python_type(self) -> type:
        """
        Get the Python type of the stored value.

        Returns:
            type: The Python type class (bool, int, float, str, list, dict)

        Examples:
            >>> value = ModelValueUnion(value="hello")
            >>> assert value.get_python_type() == str
        """
        type_map = {
            "bool": bool,
            "int": int,
            "float": float,
            "str": str,
            "list": list,
            "dict": dict,
        }
        return type_map[self.value_type]

    def as_dict(self) -> dict[str, object]:
        """
        Convert to dictionary representation.

        Returns:
            dict[str, object]: Dictionary with value, value_type, and metadata

        Examples:
            >>> value = ModelValueUnion(value=42)
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
            >>> value = ModelValueUnion(value=42)
            >>> assert value.is_primitive() is True
            >>> value = ModelValueUnion(value=[1, 2, 3])
            >>> assert value.is_primitive() is False
        """
        return self.value_type in ("bool", "int", "float", "str")

    def is_collection(self) -> bool:
        """
        Check if value is a collection type (list, dict).

        Returns:
            bool: True if value is collection, False if primitive

        Examples:
            >>> value = ModelValueUnion(value=[1, 2, 3])
            >>> assert value.is_collection() is True
            >>> value = ModelValueUnion(value=42)
            >>> assert value.is_collection() is False
        """
        return self.value_type in ("list", "dict")

    def __str__(self) -> str:
        """String representation."""
        return f"ValueUnion({self.value_type}: {self.value})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"ModelValueUnion(value_type='{self.value_type}', value={self.value!r})"

    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
        from_attributes=True,
    )


__all__ = ["ModelValueUnion"]
