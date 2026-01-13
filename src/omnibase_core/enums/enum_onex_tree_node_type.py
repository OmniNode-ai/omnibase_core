"""
Enum for OnexTreeNode types.
"""

from enum import Enum, unique


@unique
class EnumOnexTreeNodeType(str, Enum):
    """Type of an OnexTreeNode."""

    FILE = "file"
    DIRECTORY = "directory"
