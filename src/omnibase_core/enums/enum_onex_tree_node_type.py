# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Enum for OnexTreeNode types.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumOnexTreeNodeType(UtilStrValueHelper, str, Enum):
    """Type of an OnexTreeNode."""

    FILE = "file"
    DIRECTORY = "directory"


__all__ = ["EnumOnexTreeNodeType"]
