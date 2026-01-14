"""
CLI value type enumeration.

Enumeration for discriminated union types in CLI value objects.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCliValueType(StrValueHelper, str, Enum):
    """CLI value type enumeration."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DICT = "dict[str, Any]"
    LIST = "list[Any]"
    NULL = "null"


# Export the enum
__all__ = ["EnumCliValueType"]
