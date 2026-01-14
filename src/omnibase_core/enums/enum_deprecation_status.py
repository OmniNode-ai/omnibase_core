"""
Deprecation Status Enumeration.

Defines standardized deprecation lifecycle states for functions and other components.
Part of the ONEX strong typing foundation.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDeprecationStatus(StrValueHelper, str, Enum):
    """
    Deprecation status enumeration for lifecycle management.

    Provides standardized deprecation states that can be used across
    models for consistent deprecation tracking and lifecycle management.
    """

    # Active states
    ACTIVE = "active"
    STABLE = "stable"

    # Deprecation states
    DEPRECATED = "deprecated"
    DEPRECATED_WITH_REPLACEMENT = "deprecated_with_replacement"
    PENDING_REMOVAL = "pending_removal"

    # End states
    REMOVED = "removed"
    OBSOLETE = "obsolete"

    def is_active(self) -> bool:
        """Check if this status represents an active component."""
        return self in {
            EnumDeprecationStatus.ACTIVE,
            EnumDeprecationStatus.STABLE,
        }

    def is_deprecated(self) -> bool:
        """Check if this status represents a deprecated component."""
        return self in {
            EnumDeprecationStatus.DEPRECATED,
            EnumDeprecationStatus.DEPRECATED_WITH_REPLACEMENT,
            EnumDeprecationStatus.PENDING_REMOVAL,
        }

    def is_removed(self) -> bool:
        """Check if this status represents a removed component."""
        return self in {
            EnumDeprecationStatus.REMOVED,
            EnumDeprecationStatus.OBSOLETE,
        }

    def allows_usage(self) -> bool:
        """Check if this status allows component usage."""
        return self in {
            EnumDeprecationStatus.ACTIVE,
            EnumDeprecationStatus.STABLE,
            EnumDeprecationStatus.DEPRECATED,
            EnumDeprecationStatus.DEPRECATED_WITH_REPLACEMENT,
        }


# Export for use
__all__ = ["EnumDeprecationStatus"]
