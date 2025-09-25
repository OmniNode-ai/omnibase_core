"""
Numeric type enumeration.

Enumeration for handling numeric values in validation rules
to replace int | float unions.
"""

from enum import Enum, unique


@unique
class EnumNumericType(str, Enum):
    """Numeric type enumeration for validation rules."""

    INTEGER = "integer"
    FLOAT = "float"
    NUMERIC = "numeric"  # Accepts both int and float


# Export the enum
__all__ = ["EnumNumericType"]
