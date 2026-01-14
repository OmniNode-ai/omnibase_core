"""
CLI input data value type enumeration.

Enumeration for discriminated union types in CLI execution input data value objects.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCliInputValueType(StrValueHelper, str, Enum):
    """CLI input data value type enumeration."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    PATH = "path"
    UUID = "uuid"
    STRING_LIST = "string_list"


# Export the enum
__all__ = ["EnumCliInputValueType"]
