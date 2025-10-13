from __future__ import annotations

"""
Metadata node type enumeration.
"""


from enum import Enum, unique


@unique
class EnumMetadataNodeType(str, Enum):
    """Metadata node type enumeration."""

    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    MODULE = "module"
    PROPERTY = "property"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    TYPE_ALIAS = "type_alias"
    DOCUMENTATION = "documentation"
    EXAMPLE = "example"
    TEST = "test"


__all__ = ["EnumMetadataNodeType"]
