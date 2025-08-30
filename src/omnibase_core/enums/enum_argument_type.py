"""
Enum for CLI argument types.

Defines the available types for CLI command arguments.
"""

from enum import Enum


class EnumArgumentType(str, Enum):
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
    LIST = "list"
