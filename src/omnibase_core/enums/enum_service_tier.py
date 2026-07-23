# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Service Tier Enum.

Service tier classification for dependency ordering.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumServiceTier(UtilStrValueHelper, str, Enum):
    """Service tier classification for dependency ordering."""

    INFRASTRUCTURE = "infrastructure"  # Event bus, databases, monitoring
    CORE = "core"  # Registry, discovery services
    APPLICATION = "application"  # Business logic nodes
    UTILITY = "utility"  # Tools, utilities, one-off services
