"""
Operation parameter type enumeration.

Defines types for discriminated union in operation parameters.
"""

from enum import Enum, unique


@unique
class EnumOperationParameterType(str, Enum):
    """Operation parameter type enumeration for discriminated unions."""

    STRING = "string"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    LIST = "list[Any]"
    NESTED = "nested"


# Export for use
__all__ = ["EnumOperationParameterType"]
