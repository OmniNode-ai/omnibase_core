"""
Service Tier Enum.

Service tier classification for dependency ordering.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumServiceTier(StrValueHelper, str, Enum):
    """Service tier classification for dependency ordering."""

    INFRASTRUCTURE = "infrastructure"  # Event bus, databases, monitoring
    CORE = "core"  # Registry, discovery services
    APPLICATION = "application"  # Business logic nodes
    UTILITY = "utility"  # Tools, utilities, one-off services
