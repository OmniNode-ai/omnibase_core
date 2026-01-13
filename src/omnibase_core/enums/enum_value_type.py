"""
Value Type Enum.

Strongly typed enumeration for generic value type discriminators.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumValueType(StrValueHelper, str, Enum):
    """
    Strongly typed value type discriminators for ModelGenericValue.

    Used for discriminated union patterns in generic value handling.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST_STRING = "list_string"
    LIST_INTEGER = "list_integer"
    DICT = "dict"
    NULL = "null"

    @classmethod
    def is_primitive_type(cls, value_type: "EnumValueType") -> bool:
        """Check if the value type represents a primitive value."""
        return value_type in {cls.STRING, cls.INTEGER, cls.FLOAT, cls.BOOLEAN}

    @classmethod
    def is_numeric_type(cls, value_type: "EnumValueType") -> bool:
        """Check if the value type represents a numeric value."""
        return value_type in {cls.INTEGER, cls.FLOAT}

    @classmethod
    def is_collection_type(cls, value_type: "EnumValueType") -> bool:
        """Check if the value type represents a collection."""
        return value_type in {cls.DICT, cls.LIST_STRING, cls.LIST_INTEGER}

    @classmethod
    def is_list_type(cls, value_type: "EnumValueType") -> bool:
        """Check if the value type represents a list."""
        return value_type in {cls.LIST_STRING, cls.LIST_INTEGER}


# Export for use
__all__ = ["EnumValueType"]
