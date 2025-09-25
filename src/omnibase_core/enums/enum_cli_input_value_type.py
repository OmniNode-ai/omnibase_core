"""
CLI input data value type enumeration.

Enumeration for discriminated union types in CLI execution input data value objects.
"""

from enum import Enum, unique


@unique
class EnumCliInputValueType(str, Enum):
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
