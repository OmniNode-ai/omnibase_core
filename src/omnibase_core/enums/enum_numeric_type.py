"""
Numeric type enumeration.

Enumeration for handling numeric values in validation rules
to replace int | float unions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNumericType(StrValueHelper, str, Enum):
    """Numeric type enumeration for validation rules."""

    INTEGER = "integer"
    FLOAT = "float"
    NUMERIC = "numeric"  # Accepts both int and float


# Export the enum
__all__ = ["EnumNumericType"]
