"""
Metadata Node Type Enumeration.

Enumeration defining different types of metadata nodes.
"""

from enum import Enum


class ModelMetadataNodeType(str, Enum):
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


# Export for use
__all__ = ["ModelMetadataNodeType"]