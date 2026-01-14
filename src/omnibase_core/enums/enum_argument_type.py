"""
Enum for CLI argument types.

Defines the available types for CLI command arguments.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumArgumentType(StrValueHelper, str, Enum):
    """
    Enumeration of CLI argument types.

    These types define the expected data type for CLI arguments.
    """

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"
    PATH = "path"
    JSON = "json"
    LIST = "list[Any]"


__all__ = ["EnumArgumentType"]
