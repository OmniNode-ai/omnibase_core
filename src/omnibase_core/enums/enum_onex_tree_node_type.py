"""
Enum for OnexTreeNode types.
"""

from enum import Enum


class EnumOnexTreeNodeType(str, Enum):
    """Type of an OnexTreeNode."""

    FILE = "file"
    DIRECTORY = "directory"
