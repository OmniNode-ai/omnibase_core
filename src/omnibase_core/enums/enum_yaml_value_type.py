"""
YAML Value Type Enum.

Strongly typed enumeration for YAML value type discriminators.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumYamlValueType(StrValueHelper, str, Enum):
    """
    Strongly typed YAML value type discriminators.

    Used for discriminated union patterns in YAML-serializable data structures.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    SCHEMA_VALUE = "schema_value"
    DICT = "dict[str, Any]"
    LIST = "list[Any]"

    @classmethod
    def is_collection_type(cls, value_type: EnumYamlValueType) -> bool:
        """Check if the value type represents a collection."""
        return value_type in {cls.DICT, cls.LIST}

    @classmethod
    def is_structured_type(cls, value_type: EnumYamlValueType) -> bool:
        """Check if the value type represents structured data."""
        return value_type in {cls.SCHEMA_VALUE, cls.DICT, cls.LIST}

    @classmethod
    def get_collection_types(cls) -> list[EnumYamlValueType]:
        """Get all collection value types."""
        return [cls.DICT, cls.LIST]


# Export for use
__all__ = ["EnumYamlValueType"]
