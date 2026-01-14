"""
CLI context value type enumeration.

Enumeration for discriminated union types in CLI execution context value objects.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCliContextValueType(StrValueHelper, str, Enum):
    """CLI context value type enumeration."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    PATH = "path"
    UUID = "uuid"
    STRING_LIST = "string_list"


# Export the enum
__all__ = ["EnumCliContextValueType"]
