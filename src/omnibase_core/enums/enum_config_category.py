"""
Configuration category enumeration for categorizing system configurations.

Provides strongly typed categories for various configuration types
across the ONEX architecture.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumConfigCategory(StrValueHelper, str, Enum):
    """
    Strongly typed configuration categories.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for configuration categorization.
    """

    # Core system categories
    GENERATION = "generation"
    VALIDATION = "validation"
    TEMPLATE = "template"
    MAINTENANCE = "maintenance"
    RUNTIME = "runtime"

    # Infrastructure categories
    CLI = "cli"
    DISCOVERY = "discovery"
    SCHEMA = "schema"
    LOGGING = "logging"
    TESTING = "testing"

    # Generic categories
    GENERAL = "general"
    UNKNOWN = "unknown"

    @classmethod
    def get_system_categories(cls) -> list[EnumConfigCategory]:
        """Get core system configuration categories."""
        return list(_SYSTEM_CATEGORIES)

    @classmethod
    def get_infrastructure_categories(cls) -> list[EnumConfigCategory]:
        """Get infrastructure configuration categories."""
        return list(_INFRASTRUCTURE_CATEGORIES)

    @classmethod
    def is_system_category(cls, category: EnumConfigCategory) -> bool:
        """Check if category is a core system category (O(1) lookup)."""
        return category in _SYSTEM_CATEGORIES

    @classmethod
    def is_infrastructure_category(cls, category: EnumConfigCategory) -> bool:
        """Check if category is an infrastructure category (O(1) lookup)."""
        return category in _INFRASTRUCTURE_CATEGORIES


# Cached frozensets for O(1) membership lookups.
# Defined after the enum class to allow self-referential enum values.
_SYSTEM_CATEGORIES: frozenset[EnumConfigCategory] = frozenset(
    {
        EnumConfigCategory.GENERATION,
        EnumConfigCategory.VALIDATION,
        EnumConfigCategory.TEMPLATE,
        EnumConfigCategory.MAINTENANCE,
        EnumConfigCategory.RUNTIME,
    }
)

_INFRASTRUCTURE_CATEGORIES: frozenset[EnumConfigCategory] = frozenset(
    {
        EnumConfigCategory.CLI,
        EnumConfigCategory.DISCOVERY,
        EnumConfigCategory.SCHEMA,
        EnumConfigCategory.LOGGING,
        EnumConfigCategory.TESTING,
    }
)


# Export for use
__all__ = ["EnumConfigCategory"]
