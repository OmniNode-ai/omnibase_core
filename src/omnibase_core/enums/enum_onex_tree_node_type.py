"""
Enum for OnexTreeNode types.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumOnexTreeNodeType(StrValueHelper, str, Enum):
    """Type of an OnexTreeNode."""

    FILE = "file"
    DIRECTORY = "directory"


__all__ = ["EnumOnexTreeNodeType"]
