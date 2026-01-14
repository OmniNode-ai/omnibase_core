"""
Metadata node type enumeration.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMetadataNodeType(StrValueHelper, str, Enum):
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
