"""
Metadata node type enumeration.
"""

from enum import Enum


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
