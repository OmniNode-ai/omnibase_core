"""
CLI command option value type enumeration.

Enumeration for discriminated union types in CLI command option value objects.
"""

from enum import Enum, unique


@unique
class EnumCliOptionValueType(str, Enum):
    """CLI command option value type enumeration."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    UUID = "uuid"
    STRING_LIST = "string_list"


# Export the enum
__all__ = ["EnumCliOptionValueType"]
