# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Enum for permission scopes.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumPermissionScope(UtilStrValueHelper, str, Enum):
    """Permission scope levels."""

    GLOBAL = "global"
    ORGANIZATION = "organization"
    PROJECT = "project"
    TEAM = "team"
    USER = "user"
    SERVICE = "service"
    RESOURCE = "resource"


__all__ = ["EnumPermissionScope"]
