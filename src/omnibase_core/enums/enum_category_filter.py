"""
Category Filter Enum.

Strongly typed category filter values for ONEX architecture filtering operations.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCategoryFilter(StrValueHelper, str, Enum):
    """
    Strongly typed category filter values for ONEX architecture.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for category filtering operations.
    """

    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    ALL = "all"
    CUSTOM = "custom"
    ARCHIVED = "archived"

    @classmethod
    def is_hierarchical(cls, filter_type: EnumCategoryFilter) -> bool:
        """Check if the filter type represents a hierarchical level."""
        return filter_type in {
            cls.PRIMARY,
            cls.SECONDARY,
            cls.TERTIARY,
        }

    @classmethod
    def is_inclusive(cls, filter_type: EnumCategoryFilter) -> bool:
        """Check if the filter type includes multiple categories."""
        return filter_type in {
            cls.ALL,
            cls.CUSTOM,
        }

    @classmethod
    def is_exclusive(cls, filter_type: EnumCategoryFilter) -> bool:
        """Check if the filter type excludes certain items."""
        return filter_type == cls.ARCHIVED

    @classmethod
    def get_priority_level(cls, filter_type: EnumCategoryFilter) -> int:
        """Get the numeric priority level for hierarchical filters."""
        priority_map = {
            cls.PRIMARY: 1,
            cls.SECONDARY: 2,
            cls.TERTIARY: 3,
            cls.ALL: 0,
            cls.CUSTOM: 0,
            cls.ARCHIVED: -1,
        }
        return priority_map.get(filter_type, 0)

    @classmethod
    def get_hierarchical_filters(cls) -> list[EnumCategoryFilter]:
        """Get all hierarchical filter types ordered by priority."""
        return [cls.PRIMARY, cls.SECONDARY, cls.TERTIARY]

    @classmethod
    def is_active_filter(cls, filter_type: EnumCategoryFilter) -> bool:
        """Check if the filter type represents active (non-archived) content."""
        return filter_type != cls.ARCHIVED


# Export for use
__all__ = ["EnumCategoryFilter"]
