from __future__ import annotations

"""
YAML Option Type Enum.

Strongly typed enumeration for YAML dumper option value types.
"""


from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumYamlOptionType(StrValueHelper, str, Enum):
    """
    Strongly typed YAML dumper option value types.

    Used for discriminated union patterns in YAML option handling.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    BOOLEAN = "boolean"
    INTEGER = "integer"
    STRING = "string"

    @classmethod
    def is_numeric_type(cls, option_type: EnumYamlOptionType) -> bool:
        """Check if the option type represents a numeric value."""
        return option_type == cls.INTEGER

    @classmethod
    def is_primitive_type(cls, option_type: EnumYamlOptionType) -> bool:
        """Check if the option type represents a primitive value."""
        return option_type in {cls.BOOLEAN, cls.INTEGER, cls.STRING}

    @classmethod
    def get_primitive_types(cls) -> list[EnumYamlOptionType]:
        """Get all primitive option types."""
        return [cls.BOOLEAN, cls.INTEGER, cls.STRING]


# Export for use
__all__ = ["EnumYamlOptionType"]
