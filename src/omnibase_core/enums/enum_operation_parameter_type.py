"""
Operation parameter type enumeration.

Defines types for discriminated union in operation parameters.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumOperationParameterType(StrValueHelper, str, Enum):
    """Operation parameter type enumeration for discriminated unions."""

    STRING = "string"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    LIST = "list[Any]"
    NESTED = "nested"


# Export for use
__all__ = ["EnumOperationParameterType"]
