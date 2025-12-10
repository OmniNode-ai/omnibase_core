from enum import Enum


class EnumJsonValueType(str, Enum):
    """ONEX-compliant JSON value type enum for validation."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    NULL = "null"
