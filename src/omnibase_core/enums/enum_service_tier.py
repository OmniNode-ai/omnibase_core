"""
Service Tier Enum.

Service tier classification for dependency ordering.
"""

from enum import Enum, unique


@unique
class EnumServiceTier(str, Enum):
    """Service tier classification for dependency ordering."""

    INFRASTRUCTURE = "infrastructure"  # Event bus, databases, monitoring
    CORE = "core"  # Registry, discovery services
    APPLICATION = "application"  # Business logic nodes
    UTILITY = "utility"  # Tools, utilities, one-off services
