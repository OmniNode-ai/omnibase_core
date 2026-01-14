"""
Validation value type enumeration.

Enumeration for discriminated union types in validation value objects.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumValidationValueType(StrValueHelper, str, Enum):
    """Validation value type enumeration."""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    NULL = "null"


# Export the enum
__all__ = ["EnumValidationValueType"]
