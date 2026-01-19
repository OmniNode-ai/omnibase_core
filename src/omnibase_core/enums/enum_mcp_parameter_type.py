"""MCP parameter type enumeration.

Defines the JSON Schema types for MCP tool parameters.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMCPParameterType(StrValueHelper, str, Enum):
    """JSON Schema types for MCP tool parameters.

    These correspond to JSON Schema primitive and complex types:
        - STRING: Text values
        - NUMBER: Numeric values (integer or float)
        - INTEGER: Integer values only
        - BOOLEAN: True/false values
        - ARRAY: List/array of values
        - OBJECT: Nested object/dictionary
        - NULL: Null/None value
    """

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"


__all__ = ["EnumMCPParameterType"]
