"""
Validation value type enumeration.

Enumeration for discriminated union types in validation value objects.
"""

from enum import Enum, unique


@unique
class EnumValidationValueType(str, Enum):
    """Validation value type enumeration."""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    NULL = "null"


# Export the enum
__all__ = ["EnumValidationValueType"]
