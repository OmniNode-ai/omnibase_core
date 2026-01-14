"""
ModelPolicyValue

SECURITY-CRITICAL: Type-safe wrapper for security policy values with sensitive data marking.

This model provides automatic type inference and validation for policy value union types,
replacing bare Union[None, bool, dict, float, int, list, str] patterns with structured
type safety for security-critical applications.

Features:
- Automatic type inference from value
- Support for None/optional values (critical for security policies)
- Sensitive data marking capability
- Type consistency validation
- Support for nested collections (List[Any], Dict[str, Any])
- Comprehensive security validation
- DoS protection via size limits
- Full mypy strict mode compliance

Security Features:
- Maximum list size limit to prevent DoS attacks (10,000 items)
- Maximum dict size limit to prevent DoS attacks (1,000 items)
- String key validation for dict values (JSON compatibility)
- NaN and infinity detection for float values
- Sensitive data marking for audit logging
- Input validation for all types

Usage Examples:
    # Automatic type inference with None
    >>> value = ModelPolicyValue(value=None)
    >>> assert value.value_type == "none"
    >>> assert value.is_none() is True

    # Sensitive data marking
    >>> secret = ModelPolicyValue(value="password123", is_sensitive=True)
    >>> assert secret.is_sensitive is True
    >>> assert secret.value_type == "str"

    # Explicit type specification
    >>> value = ModelPolicyValue(value="hello", value_type="str")
    >>> assert value.value_type == "str"

    # Complex types for policy configuration
    >>> policy_data = ModelPolicyValue(value={"max_attempts": 3, "timeout": 30})
    >>> assert policy_data.value_type == "dict"
    >>> assert policy_data.get_python_type() == dict

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.errors modules
- pydantic modules
"""

from __future__ import annotations

import math
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.typed_dict_policy_value_data import TypedDictPolicyValueData


class ModelPolicyValue(BaseModel):
    """
    SECURITY-CRITICAL: Type-safe wrapper for security policy values.

    Replaces bare Union[None, bool, dict, float, int, list, str] patterns
    with structured, validated union types that preserve type information
    and mark sensitive data for security audit purposes.

    The model automatically infers the type from the provided value
    when value_type is not explicitly specified. Supports None values
    for optional policy configuration.

    Attributes:
        value: The actual value (None, bool, int, float, str, list, or dict)
        value_type: Type discriminator ("none", "bool", "int", "float", "str", "list", "dict")
        is_sensitive: Flag indicating if value contains sensitive data (default: False)
        metadata: Optional metadata for the value (string-to-string mapping)

    Security Notes:
        - Use is_sensitive=True for passwords, tokens, API keys, secrets
        - Sensitive values should be masked in logs and audit trails
        - DoS protection via collection size limits enforced automatically
        - NaN and infinity rejected for float values to prevent calculation errors

    Examples:
        # Automatic type inference
        >>> value = ModelPolicyValue(value=42)
        >>> assert value.value_type == "int"

        # None handling
        >>> optional_value = ModelPolicyValue(value=None)
        >>> assert optional_value.is_none() is True

        # Sensitive data
        >>> secret = ModelPolicyValue(value="api_key_123", is_sensitive=True)
        >>> assert secret.is_sensitive is True

        # Complex policy data
        >>> config = ModelPolicyValue(value={"rate_limit": 100, "timeout": 30})
        >>> assert config.value_type == "dict"
    """

    # Security constants - prevent DoS via large collections
    # ClassVar prevents per-instance override attacks
    MAX_LIST_SIZE: ClassVar[int] = 10000
    MAX_DICT_SIZE: ClassVar[int] = 1000

    # ONEX_EXCLUDE: dict_str_any - security policy values support arbitrary nested data
    value: None | bool | int | float | str | list[Any] | dict[str, Any] = Field(
        description="The actual policy value (supports None for optional policies)",
    )

    value_type: Literal["none", "bool", "int", "float", "str", "list", "dict"] = Field(
        description="Type discriminator for the value",
    )

    is_sensitive: bool = Field(
        default=False,
        description="Flag indicating if value contains sensitive data (passwords, tokens, keys)",
    )

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Optional string metadata for audit and tracking",
    )

    @model_validator(mode="before")
    @classmethod
    # ONEX_EXCLUDE: dict_str_any - pydantic validator return type
    def infer_value_type(cls, data: Any) -> dict[str, Any]:
        """
        Automatically infer value_type from value if not provided.

        This validator runs before field validation and auto-populates
        the value_type field based on the Python type of the value.

        Type inference rules:
        - None is checked first for optional values
        - bool is checked before int (since bool is subclass of int)
        - int, float, str are checked in order
        - list and dict are checked for collections

        Args:
            data: Input data (dict or value)

        Returns:
            dict[str, Any]: Data with value_type populated

        Raises:
            ModelOnexError: If value type is unsupported

        Security Notes:
            - Type inference ensures consistent handling across all policy values
            - Prevents type confusion attacks by explicit type checking
        """
        # Ensure data is a dict (help mypy with type narrowing)
        # ONEX_EXCLUDE: dict_str_any - pydantic validator input data
        data_dict: dict[str, Any]
        if not isinstance(data, dict):
            data_dict = {"value": data}
        else:
            data_dict = data

        # If value_type already specified, validate it's correct
        if "value_type" in data_dict:
            return data_dict

        # Infer type from value
        value = data_dict.get("value")

        # Check None FIRST for optional values (CRITICAL for security policies)
        if value is None:
            data_dict["value_type"] = "none"
        # Check bool BEFORE int (bool is subclass of int in Python)
        elif isinstance(value, bool):
            data_dict["value_type"] = "bool"
        elif isinstance(value, int):
            data_dict["value_type"] = "int"
        elif isinstance(value, float):
            data_dict["value_type"] = "float"
        elif isinstance(value, str):
            data_dict["value_type"] = "str"
        elif isinstance(value, list):
            data_dict["value_type"] = "list"
        elif isinstance(value, dict):
            data_dict["value_type"] = "dict"
        else:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unsupported policy value type: {type(value).__name__}",
                context={
                    "value_type": type(value).__name__,
                    "supported_types": "none, bool, int, float, str, list, dict",
                    "security_note": "Only explicitly supported types allowed for security policies",
                },
            )

        return data_dict

    @model_validator(mode="after")
    def validate_value_type_match(self) -> ModelPolicyValue:
        """
        Validate that value matches the declared value_type.

        This validator runs after field validation and ensures type consistency
        between the value and value_type fields. Implements security validations
        to prevent DoS attacks and ensure data integrity.

        Special handling:
        - None is treated as valid "none" type
        - bool is checked before int (bool is subclass of int)
        - float NaN and infinity values are detected and rejected
        - Empty strings are allowed (for optional string policies)
        - Empty collections are allowed
        - Dict keys must be strings for JSON compatibility

        Returns:
            ModelPolicyValue: Self if validation passes

        Raises:
            ModelOnexError: If value doesn't match declared type or fails security validation

        Security Validations:
        - List size limits enforced to prevent memory exhaustion
        - Dict size limits enforced to prevent memory exhaustion
        - Float special values (NaN, inf) rejected to prevent calculation errors
        - String keys required for dict to ensure JSON serialization
        """
        # Type checking map - note bool must be checked before int, None checked first
        type_checks = {
            "none": lambda x: x is None,
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
                    "allowed_types": "none, bool, int, float, str, list, dict",
                },
            )

        if not type_check(self.value):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Policy value type mismatch: expected {self.value_type}, got {type(self.value).__name__}",
                context={
                    "expected_type": self.value_type,
                    "actual_type": type(self.value).__name__,
                    "value": str(self.value) if not self.is_sensitive else "[REDACTED]",
                    "security_note": "Type consistency required for security policies",
                },
            )

        # Type-specific security validation with type narrowing for mypy
        if self.value_type == "float":
            # Type narrowing: at this point we know value is float
            if isinstance(self.value, float):
                # Reject NaN and infinity for security policies
                if math.isnan(self.value) or math.isinf(self.value):
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message="Policy float value cannot be NaN or infinity",
                        context={
                            "value": str(self.value),
                            "is_nan": math.isnan(self.value),
                            "is_inf": math.isinf(self.value),
                            "security_note": "NaN/infinity rejected to prevent calculation errors",
                        },
                    )

        elif self.value_type == "list":
            # Type narrowing: at this point we know value is list
            if isinstance(self.value, list):
                # Check list size for DoS prevention (SECURITY-CRITICAL)
                if len(self.value) > self.MAX_LIST_SIZE:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Policy list exceeds maximum size of {self.MAX_LIST_SIZE}",
                        context={
                            "list_size": len(self.value),
                            "max_size": self.MAX_LIST_SIZE,
                            "security_note": "Size limit enforced to prevent DoS attacks",
                        },
                    )

        elif self.value_type == "dict":
            # Type narrowing: at this point we know value is dict
            if isinstance(self.value, dict):
                # Check dict size for DoS prevention (SECURITY-CRITICAL)
                if len(self.value) > self.MAX_DICT_SIZE:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Policy dict exceeds maximum size of {self.MAX_DICT_SIZE}",
                        context={
                            "dict_size": len(self.value),
                            "max_size": self.MAX_DICT_SIZE,
                            "security_note": "Size limit enforced to prevent DoS attacks",
                        },
                    )

                # Validate all keys are strings for JSON compatibility (SECURITY)
                non_string_keys = [k for k in self.value if not isinstance(k, str)]
                if non_string_keys:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message="Policy dict keys must be strings for JSON compatibility",
                        context={
                            "non_string_keys": str(non_string_keys[:5]),  # Show first 5
                            "non_string_key_count": len(non_string_keys),
                            "security_note": "String keys required for secure serialization",
                        },
                    )

        return self

    # ONEX_EXCLUDE: dict_str_any - returns stored policy value which may contain arbitrary dict
    def get_value(
        self,
    ) -> None | bool | int | float | str | list[Any] | dict[str, Any]:
        """
        Get the stored policy value with proper type.

        Returns:
            The actual value with its native Python type (may be None)

        Security Notes:
            - Caller is responsible for masking sensitive values in logs
            - Use is_sensitive flag to determine if masking is required

        Examples:
            >>> value = ModelPolicyValue(value=42)
            >>> assert value.get_value() == 42
            >>> assert isinstance(value.get_value(), int)

            >>> optional = ModelPolicyValue(value=None)
            >>> assert optional.get_value() is None
        """
        return self.value

    def get_type(self) -> str:
        """
        Get the value type as string.

        Returns:
            str: The value type ("none", "bool", "int", "float", "str", "list", "dict")

        Examples:
            >>> value = ModelPolicyValue(value="hello")
            >>> assert value.get_type() == "str"
        """
        return self.value_type

    def is_none(self) -> bool:
        """
        Check if value is None (optional policy value).

        Returns:
            bool: True if value is None, False otherwise

        Examples:
            >>> value = ModelPolicyValue(value=None)
            >>> assert value.is_none() is True

            >>> value = ModelPolicyValue(value=42)
            >>> assert value.is_none() is False
        """
        return self.value_type == "none"

    def get_python_type(self) -> type:
        """
        Get the Python type of the stored value.

        Returns:
            type: The Python type class (type(None), bool, int, float, str, list, dict)

        Examples:
            >>> value = ModelPolicyValue(value="hello")
            >>> assert value.get_python_type() == str

            >>> optional = ModelPolicyValue(value=None)
            >>> assert value.get_python_type() == type(None)
        """
        type_map = {
            "none": type(None),
            "bool": bool,
            "int": int,
            "float": float,
            "str": str,
            "list": list,
            "dict": dict,
        }
        return type_map[self.value_type]

    def as_dict(self) -> TypedDictPolicyValueData:
        """
        Convert to dictionary representation.

        Returns:
            TypedDictPolicyValueData: Dictionary with value, value_type, is_sensitive, and metadata

        Security Notes:
            - Sensitive values are NOT masked in this output
            - Caller must handle sensitive flag appropriately
            - Use for serialization and audit logging with proper masking

        Examples:
            >>> value = ModelPolicyValue(value=42, is_sensitive=False)
            >>> data = value.as_dict()
            >>> assert data["value"] == 42
            >>> assert data["value_type"] == "int"
            >>> assert data["is_sensitive"] is False
        """
        return TypedDictPolicyValueData(
            value=self.value,
            value_type=self.value_type,
            is_sensitive=self.is_sensitive,
            metadata=self.metadata,
        )

    def is_primitive(self) -> bool:
        """
        Check if value is a primitive type (none, bool, int, float, str).

        Returns:
            bool: True if value is primitive, False if collection

        Examples:
            >>> value = ModelPolicyValue(value=42)
            >>> assert value.is_primitive() is True

            >>> value = ModelPolicyValue(value=[1, 2, 3])
            >>> assert value.is_primitive() is False

            >>> value = ModelPolicyValue(value=None)
            >>> assert value.is_primitive() is True
        """
        return self.value_type in ("none", "bool", "int", "float", "str")

    def is_collection(self) -> bool:
        """
        Check if value is a collection type (list, dict).

        Returns:
            bool: True if value is collection, False if primitive

        Examples:
            >>> value = ModelPolicyValue(value=[1, 2, 3])
            >>> assert value.is_collection() is True

            >>> value = ModelPolicyValue(value=42)
            >>> assert value.is_collection() is False

            >>> value = ModelPolicyValue(value=None)
            >>> assert value.is_collection() is False
        """
        return self.value_type in ("list", "dict")

    def __str__(self) -> str:
        """
        String representation with sensitive data protection.

        Security Notes:
            - Sensitive values are masked as [SENSITIVE]
            - Use for logging and debugging output
        """
        value_display = "[SENSITIVE]" if self.is_sensitive else self.value
        return f"PolicyValue({self.value_type}: {value_display})"

    def __repr__(self) -> str:
        """
        Detailed representation with sensitive data protection.

        Security Notes:
            - Sensitive values are masked as [REDACTED]
            - Use for debugging and development
        """
        value_display = "[REDACTED]" if self.is_sensitive else repr(self.value)
        return f"ModelPolicyValue(value_type='{self.value_type}', value={value_display}, is_sensitive={self.is_sensitive})"

    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
    )


__all__ = ["ModelPolicyValue"]
