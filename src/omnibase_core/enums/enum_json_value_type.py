from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumJsonValueType(StrValueHelper, str, Enum):
    """ONEX-compliant JSON value type enum for validation."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    NULL = "null"


__all__ = ["EnumJsonValueType"]
