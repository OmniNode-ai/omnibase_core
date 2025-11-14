from __future__ import annotations

"""
Numeric Value Type Enum.

Strongly typed enumeration for numeric value type discriminators.
Used in ModelNumericValue for type-safe numeric union handling.
"""

from enum import Enum, unique


@unique
class EnumNumericValueType(str, Enum):
    """
    Strongly typed numeric value type discriminators.

    Used for discriminated union patterns in numeric value handling.
    Replaces Union[float, int, str] patterns with structured type safety.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    FLOAT = "float"
    INT = "int"
    STRING = "string"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_numeric_type(cls, value_type: EnumNumericValueType) -> bool:
        """Check if the value type represents a numeric value."""
        return value_type in {cls.INT, cls.FLOAT}

    @classmethod
    def get_numeric_types(cls) -> list[EnumNumericValueType]:
        """Get all numeric value types."""
        return [cls.INT, cls.FLOAT]


# Export for use
__all__ = ["EnumNumericValueType"]
