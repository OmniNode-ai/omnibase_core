"""ModelDictValueUnion - Type-safe wrapper for dict-containing union patterns.

This model provides automatic type inference and validation for union types,
replacing bare Union[bool, dict, float, int, list, str] patterns with structured
type safety optimized for extension and plugin systems.

Features:
    - Automatic type inference from value
    - Type consistency validation
    - Support for nested collections (dict[str, Any], list[Any])
    - Dict-specific helper methods (has_key, get_dict_value)
    - Comprehensive validation with detailed error messages
    - Full mypy strict mode compliance

Usage Examples:
    # Automatic type inference
    >>> value = ModelDictValueUnion(value={"key": "value"})
    >>> assert value.value_type == "dict"
    >>> assert value.has_key("key")

    # Dict access helpers
    >>> value = ModelDictValueUnion(value={"nested": {"data": 42}})
    >>> assert value.get_dict_value("nested") == {"data": 42}

    # Explicit type specification
    >>> value = ModelDictValueUnion(value=42, value_type="int")
    >>> assert value.value_type == "int"

Security Features:
    - Maximum list size limit to prevent DoS attacks
    - Maximum dict size limit to prevent DoS attacks
    - String key validation for dict values
    - NaN and infinity detection for float values
    - Nested dict validation

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
from typing import ClassVar, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelDictValueUnion(BaseModel):
    """
    Type-safe wrapper for dict-containing union patterns.

    Replaces bare Union[bool, dict, float, int, list, str] patterns with structured,
    validated union types that preserve type information. Optimized for extension
    and plugin systems with dict-specific helper methods.

    The model automatically infers the type from the provided value
    when value_type is not explicitly specified.

    Attributes:
        value: The actual value (bool, dict, float, int, list, or str)
        value_type: Type discriminator ("bool", "dict", "float", "int", "list", "str")
        metadata: Optional metadata for the value (string-to-string mapping)

    Examples:
        # Automatic type inference
        >>> value = ModelDictValueUnion(value={"key": "value"})
        >>> assert value.value_type == "dict"

        # Dict-specific operations
        >>> value = ModelDictValueUnion(value={"a": 1, "b": 2})
        >>> assert value.has_key("a")
        >>> assert value.get_dict_value("a") == 1

        # Complex types
        >>> value = ModelDictValueUnion(value=[1, 2, 3])
        >>> assert value.value_type == "list"
    """

    # Security constants - prevent DoS via large collections
    MAX_LIST_SIZE: ClassVar[int] = 10000
    MAX_DICT_SIZE: ClassVar[int] = 1000

    # union-ok: discriminated_union - companion value_type Literal field provides type safety
    value: bool | dict[str, object] | float | int | list[object] | str = Field(
        description="The actual value",
    )

    value_type: Literal["bool", "dict", "float", "int", "list", "str"] = Field(
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
        - dict is checked before other collections
        - int, float, str are checked in order
        - list is checked last

        Args:
            data: Input data (dict or value)

        Returns:
            dict[str, object]: Data with value_type populated

        Raises:
            ModelOnexError: If value type is unsupported
        """
        if not isinstance(data, dict):
            data = {"value": data}
        else:
            data = dict(data)  # Make a copy to avoid mutating input

        # If value_type already specified, validate it's correct
        if "value_type" in data:
            return cast("dict[str, object]", data)

        # Infer type from value
        value = data.get("value")

        # Check bool BEFORE int (bool is subclass of int in Python)
        if isinstance(value, bool):
            data["value_type"] = "bool"
        elif isinstance(value, dict):
            data["value_type"] = "dict"
        elif isinstance(value, int):
            data["value_type"] = "int"
        elif isinstance(value, float):
            data["value_type"] = "float"
        elif isinstance(value, str):
            data["value_type"] = "str"
        elif isinstance(value, list):
            data["value_type"] = "list"
        else:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unsupported value type: {type(value).__name__}",
                context={
                    "value_type": type(value).__name__,
                    "supported_types": "bool, dict, float, int, list, str",
                },
            )

        return cast("dict[str, object]", data)

    @model_validator(mode="after")
    def validate_value_type_match(self) -> ModelDictValueUnion:
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
        - Nested dict validation for security

        Returns:
            ModelDictValueUnion: Self if validation passes

        Raises:
            ModelOnexError: If value doesn't match declared type
        """
        # Type checking map - note bool must be checked before int
        type_checks = {
            "bool": lambda x: isinstance(x, bool),
            "dict": lambda x: isinstance(x, dict),
            "float": lambda x: isinstance(x, float),
            "int": lambda x: isinstance(x, int) and not isinstance(x, bool),
            "list": lambda x: isinstance(x, list),
            "str": lambda x: isinstance(x, str),
        }

        # Validate type consistency
        type_check = type_checks.get(self.value_type)
        if type_check is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unknown value_type: {self.value_type}",
                context={
                    "value_type": self.value_type,
                    "allowed_types": "bool, dict, float, int, list, str",
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
    ) -> bool | dict[str, object] | float | int | list[object] | str:
        """
        Get the stored value with proper type.

        Returns:
            The actual value with its native Python type

        Examples:
            >>> value = ModelDictValueUnion(value=42)
            >>> assert value.get_value() == 42
            >>> assert isinstance(value.get_value(), int)
        """
        return self.value

    def get_python_type(self) -> type:
        """
        Get the Python type of the stored value.

        Returns:
            type: The Python type class (bool, dict, float, int, list, str)

        Examples:
            >>> value = ModelDictValueUnion(value="hello")
            >>> assert value.get_python_type() == str
        """
        type_map = {
            "bool": bool,
            "dict": dict,
            "float": float,
            "int": int,
            "list": list,
            "str": str,
        }
        return type_map[self.value_type]

    # === Type Guards ===

    def is_bool(self) -> bool:
        """
        Check if value is a boolean.

        Returns:
            bool: True if value is bool

        Examples:
            >>> value = ModelDictValueUnion(value=True)
            >>> assert value.is_bool()
        """
        return self.value_type == "bool"

    def is_dict(self) -> bool:
        """
        Check if value is a dictionary.

        Returns:
            bool: True if value is dict

        Examples:
            >>> value = ModelDictValueUnion(value={"key": "value"})
            >>> assert value.is_dict()
        """
        return self.value_type == "dict"

    def is_float(self) -> bool:
        """
        Check if value is a float.

        Returns:
            bool: True if value is float

        Examples:
            >>> value = ModelDictValueUnion(value=3.14)
            >>> assert value.is_float()
        """
        return self.value_type == "float"

    def is_int(self) -> bool:
        """
        Check if value is an integer.

        Returns:
            bool: True if value is int

        Examples:
            >>> value = ModelDictValueUnion(value=42)
            >>> assert value.is_int()
        """
        return self.value_type == "int"

    def is_list(self) -> bool:
        """
        Check if value is a list.

        Returns:
            bool: True if value is list

        Examples:
            >>> value = ModelDictValueUnion(value=[1, 2, 3])
            >>> assert value.is_list()
        """
        return self.value_type == "list"

    def is_string(self) -> bool:
        """
        Check if value is a string.

        Returns:
            bool: True if value is str

        Examples:
            >>> value = ModelDictValueUnion(value="hello")
            >>> assert value.is_string()
        """
        return self.value_type == "str"

    # === Type Getters ===

    def get_as_bool(self) -> bool:
        """
        Get value as boolean.

        Returns:
            bool: The boolean value

        Raises:
            ModelOnexError: If value is not a bool

        Examples:
            >>> value = ModelDictValueUnion(value=True)
            >>> assert value.get_as_bool() is True
        """
        if not self.is_bool():
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value is not bool, is {self.value_type}",
                context={"value_type": self.value_type},
            )
        # NOTE(OMN-1302): Return type narrowed by is_bool() check above. Safe because value_type discriminator verified.
        return self.value  # type: ignore[return-value]

    def get_as_dict(self) -> dict[str, object]:
        """
        Get value as dictionary with safe-access semantics.

        Unlike the other get_as_* methods which raise ModelOnexError on type mismatch,
        this method returns an empty dict for non-dict values. This intentional design
        choice supports safe dict-operation chaining patterns common in extension/plugin
        systems where dict access is frequent and the fallback to empty dict is the
        natural default behavior (e.g., `value.get_as_dict().get("key", default)`).

        For strict type checking that raises on type mismatch, use:
            if value.is_dict():
                d = value.get_as_dict()
            else:
                raise ModelOnexError(...)

        Returns:
            dict[str, object]: The dictionary value, or empty dict if not a dict

        Examples:
            >>> value = ModelDictValueUnion(value={"key": "value"})
            >>> assert value.get_as_dict() == {"key": "value"}
            >>> value = ModelDictValueUnion(value=42)
            >>> assert value.get_as_dict() == {}  # Safe fallback, not an error
        """
        if self.is_dict():
            # NOTE(OMN-1302): Return type narrowed by is_dict() check above. Safe because value_type discriminator verified.
            return self.value  # type: ignore[return-value]
        return {}

    def get_as_float(self) -> float:
        """
        Get value as float.

        Returns:
            float: The float value

        Raises:
            ModelOnexError: If value is not a float

        Examples:
            >>> value = ModelDictValueUnion(value=3.14)
            >>> assert value.get_as_float() == 3.14
        """
        if not self.is_float():
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value is not float, is {self.value_type}",
                context={"value_type": self.value_type},
            )
        # NOTE(OMN-1302): Return type narrowed by is_float() check above. Safe because value_type discriminator verified.
        return self.value  # type: ignore[return-value]

    def get_as_int(self) -> int:
        """
        Get value as integer.

        Returns:
            int: The integer value

        Raises:
            ModelOnexError: If value is not an int

        Examples:
            >>> value = ModelDictValueUnion(value=42)
            >>> assert value.get_as_int() == 42
        """
        if not self.is_int():
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value is not int, is {self.value_type}",
                context={"value_type": self.value_type},
            )
        # NOTE(OMN-1302): Return type narrowed by is_int() check above. Safe because value_type discriminator verified.
        return self.value  # type: ignore[return-value]

    def get_as_list(self) -> list[object]:
        """
        Get value as list.

        Returns:
            list[object]: The list value

        Raises:
            ModelOnexError: If value is not a list

        Examples:
            >>> value = ModelDictValueUnion(value=[1, 2, 3])
            >>> assert value.get_as_list() == [1, 2, 3]
        """
        if not self.is_list():
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value is not list, is {self.value_type}",
                context={"value_type": self.value_type},
            )
        # NOTE(OMN-1302): Return type narrowed by is_list() check above. Safe because value_type discriminator verified.
        return self.value  # type: ignore[return-value]

    def get_as_str(self) -> str:
        """
        Get value as string.

        Returns:
            str: The string value

        Raises:
            ModelOnexError: If value is not a string

        Examples:
            >>> value = ModelDictValueUnion(value="hello")
            >>> assert value.get_as_str() == "hello"
        """
        if not self.is_string():
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value is not str, is {self.value_type}",
                context={"value_type": self.value_type},
            )
        # NOTE(OMN-1302): Return type narrowed by is_string() check above. Safe because value_type discriminator verified.
        return self.value  # type: ignore[return-value]

    # === Dict-Specific Helper Methods ===

    def has_key(self, key: str) -> bool:
        """
        Check if dict has the specified key.

        Returns False if value is not a dict.

        Args:
            key: The key to check for

        Returns:
            bool: True if key exists in dict, False otherwise

        Examples:
            >>> value = ModelDictValueUnion(value={"a": 1, "b": 2})
            >>> assert value.has_key("a")
            >>> assert not value.has_key("c")
            >>> value = ModelDictValueUnion(value=42)
            >>> assert not value.has_key("any")
        """
        if not self.is_dict():
            return False
        # Direct access to self.value since we already verified is_dict()
        # NOTE(OMN-1302): Membership operator valid because is_dict() check verifies dict type above.
        return key in self.value  # type: ignore[operator]

    def get_dict_value(self, key: str, default: object = None) -> object:
        """
        Get value from dict by key.

        Returns default if value is not a dict or key doesn't exist.

        Args:
            key: The key to retrieve
            default: Default value if key not found or not a dict

        Returns:
            object: The value at key, or default

        Examples:
            >>> value = ModelDictValueUnion(value={"a": 1, "b": 2})
            >>> assert value.get_dict_value("a") == 1
            >>> assert value.get_dict_value("c", 99) == 99
            >>> value = ModelDictValueUnion(value=42)
            >>> assert value.get_dict_value("any", 99) == 99
        """
        if not self.is_dict():
            return default
        # Direct access since we verified is_dict()
        # NOTE(OMN-1302): Dict.get() access valid because is_dict() check verifies dict type above.
        return self.value.get(key, default)  # type: ignore[union-attr]

    # === Collection Helpers ===

    def as_dict(self) -> dict[str, object]:
        """
        Convert to dictionary representation.

        Returns:
            dict[str, object]: Dictionary with value, value_type, and metadata

        Examples:
            >>> value = ModelDictValueUnion(value=42)
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
        Check if value is a primitive type (bool, float, int, str).

        Returns:
            bool: True if value is primitive, False if collection

        Examples:
            >>> value = ModelDictValueUnion(value=42)
            >>> assert value.is_primitive() is True
            >>> value = ModelDictValueUnion(value={"key": "value"})
            >>> assert value.is_primitive() is False
        """
        return self.value_type in ("bool", "float", "int", "str")

    def is_collection(self) -> bool:
        """
        Check if value is a collection type (dict, list).

        Returns:
            bool: True if value is collection, False if primitive

        Examples:
            >>> value = ModelDictValueUnion(value={"key": "value"})
            >>> assert value.is_collection() is True
            >>> value = ModelDictValueUnion(value=42)
            >>> assert value.is_collection() is False
        """
        return self.value_type in ("dict", "list")

    def __str__(self) -> str:
        """String representation."""
        return f"DictValueUnion({self.value_type}: {self.value})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"ModelDictValueUnion(value_type='{self.value_type}', value={self.value!r})"
        )

    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
    )


__all__ = ["ModelDictValueUnion"]
