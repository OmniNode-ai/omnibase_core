from __future__ import annotations

"""
Discriminated Value Type Enum.

Strongly typed enumeration for discriminated value type discriminators.
Used in ModelDiscriminatedValue for type-safe union handling.
"""

from enum import Enum, unique


@unique
class EnumDiscriminatedValueType(str, Enum):
    """
    Strongly typed discriminated value type discriminators.

    Used for discriminated union patterns in primitive and complex value handling.
    Replaces Union[bool, float, int, str] and Union[bool, dict, float, int, list, str]
    patterns with structured type safety.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    BOOL = "bool"
    FLOAT = "float"
    INT = "int"
    STR = "str"
    DICT = "dict"
    LIST = "list"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_primitive_type(cls, value_type: EnumDiscriminatedValueType) -> bool:
        """Check if the value type represents a primitive value."""
        return value_type in {cls.BOOL, cls.FLOAT, cls.INT, cls.STR}

    @classmethod
    def is_numeric_type(cls, value_type: EnumDiscriminatedValueType) -> bool:
        """Check if the value type represents a numeric value."""
        return value_type in {cls.INT, cls.FLOAT}

    @classmethod
    def is_collection_type(cls, value_type: EnumDiscriminatedValueType) -> bool:
        """Check if the value type represents a collection."""
        return value_type in {cls.DICT, cls.LIST}

    @classmethod
    def get_primitive_types(cls) -> list[EnumDiscriminatedValueType]:
        """Get all primitive value types."""
        return [cls.BOOL, cls.FLOAT, cls.INT, cls.STR]

    @classmethod
    def get_numeric_types(cls) -> list[EnumDiscriminatedValueType]:
        """Get all numeric value types."""
        return [cls.INT, cls.FLOAT]

    @classmethod
    def get_collection_types(cls) -> list[EnumDiscriminatedValueType]:
        """Get all collection value types."""
        return [cls.DICT, cls.LIST]


# Export for use
__all__ = ["EnumDiscriminatedValueType"]
