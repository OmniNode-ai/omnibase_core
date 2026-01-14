"""
Flexible Value Type Enum.

Strongly typed enumeration for flexible value type discriminators.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumFlexibleValueType(StrValueHelper, str, Enum):
    """
    Strongly typed flexible value type discriminators.

    Used for discriminated union patterns in flexible value handling.
    Replaces Union[str, int, float, bool, dict[str, Any], list[Any], UUID, None] patterns
    with structured type safety.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DICT = "dict[str, Any]"
    LIST = "list[Any]"
    UUID = "uuid"
    NONE = "none"

    @classmethod
    def is_primitive_type(cls, value_type: EnumFlexibleValueType) -> bool:
        """Check if the value type represents a primitive value."""
        return value_type in {cls.STRING, cls.INTEGER, cls.FLOAT, cls.BOOLEAN}

    @classmethod
    def is_numeric_type(cls, value_type: EnumFlexibleValueType) -> bool:
        """Check if the value type represents a numeric value."""
        return value_type in {cls.INTEGER, cls.FLOAT}

    @classmethod
    def is_collection_type(cls, value_type: EnumFlexibleValueType) -> bool:
        """Check if the value type represents a collection."""
        return value_type in {cls.DICT, cls.LIST}

    @classmethod
    def is_none_type(cls, value_type: EnumFlexibleValueType) -> bool:
        """Check if the value type represents None."""
        return value_type == cls.NONE

    @classmethod
    def is_object_type(cls, value_type: EnumFlexibleValueType) -> bool:
        """Check if the value type represents an object (UUID, dict[str, Any], list[Any])."""
        return value_type in {cls.UUID, cls.DICT, cls.LIST}

    @classmethod
    def get_primitive_types(cls) -> list[EnumFlexibleValueType]:
        """Get all primitive value types."""
        return [cls.STRING, cls.INTEGER, cls.FLOAT, cls.BOOLEAN]

    @classmethod
    def get_numeric_types(cls) -> list[EnumFlexibleValueType]:
        """Get all numeric value types."""
        return [cls.INTEGER, cls.FLOAT]

    @classmethod
    def get_collection_types(cls) -> list[EnumFlexibleValueType]:
        """Get all collection value types."""
        return [cls.DICT, cls.LIST]

    @classmethod
    def get_object_types(cls) -> list[EnumFlexibleValueType]:
        """Get all object value types."""
        return [cls.UUID, cls.DICT, cls.LIST]


# Export for use
__all__ = ["EnumFlexibleValueType"]
