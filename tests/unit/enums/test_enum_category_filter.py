"""
Unit tests for EnumCategoryFilter.

Test coverage for category filter enumeration and helper methods.
"""

import pytest
from src.omnibase_core.enums import EnumCategoryFilter


class TestEnumCategoryFilter:
    """Test cases for EnumCategoryFilter."""

    def test_enum_values(self):
        """Test all enum values are present."""
        expected_values = {
            "PRIMARY", "SECONDARY", "TERTIARY", "ALL", "CUSTOM", "ARCHIVED"
        }
        actual_values = {filter_type.value for filter_type in EnumCategoryFilter}
        assert actual_values == expected_values

    def test_string_inheritance(self):
        """Test that enum inherits from str."""
        assert isinstance(EnumCategoryFilter.PRIMARY, str)
        assert EnumCategoryFilter.PRIMARY == "PRIMARY"

    def test_is_hierarchical(self):
        """Test hierarchical classification."""
        hierarchical_filters = {
            EnumCategoryFilter.PRIMARY,
            EnumCategoryFilter.SECONDARY,
            EnumCategoryFilter.TERTIARY,
        }

        for filter_type in EnumCategoryFilter:
            expected = filter_type in hierarchical_filters
            actual = EnumCategoryFilter.is_hierarchical(filter_type)
            assert actual == expected, f"{filter_type} hierarchical classification failed"

    def test_is_inclusive(self):
        """Test inclusive classification."""
        inclusive_filters = {
            EnumCategoryFilter.ALL,
            EnumCategoryFilter.CUSTOM,
        }

        for filter_type in EnumCategoryFilter:
            expected = filter_type in inclusive_filters
            actual = EnumCategoryFilter.is_inclusive(filter_type)
            assert actual == expected, f"{filter_type} inclusive classification failed"

    def test_is_exclusive(self):
        """Test exclusive classification."""
        for filter_type in EnumCategoryFilter:
            expected = filter_type == EnumCategoryFilter.ARCHIVED
            actual = EnumCategoryFilter.is_exclusive(filter_type)
            assert actual == expected, f"{filter_type} exclusive classification failed"

    def test_get_priority_level(self):
        """Test priority level mapping."""
        priority_map = {
            EnumCategoryFilter.PRIMARY: 1,
            EnumCategoryFilter.SECONDARY: 2,
            EnumCategoryFilter.TERTIARY: 3,
            EnumCategoryFilter.ALL: 0,
            EnumCategoryFilter.CUSTOM: 0,
            EnumCategoryFilter.ARCHIVED: -1,
        }

        for filter_type, expected_priority in priority_map.items():
            actual_priority = EnumCategoryFilter.get_priority_level(filter_type)
            assert actual_priority == expected_priority

    def test_get_hierarchical_filters(self):
        """Test hierarchical filters retrieval."""
        expected_filters = [
            EnumCategoryFilter.PRIMARY,
            EnumCategoryFilter.SECONDARY,
            EnumCategoryFilter.TERTIARY
        ]
        actual_filters = EnumCategoryFilter.get_hierarchical_filters()
        assert actual_filters == expected_filters

    def test_is_active_filter(self):
        """Test active filter classification."""
        for filter_type in EnumCategoryFilter:
            expected = filter_type != EnumCategoryFilter.ARCHIVED
            actual = EnumCategoryFilter.is_active_filter(filter_type)
            assert actual == expected, f"{filter_type} active filter classification failed"

    def test_str_representation(self):
        """Test string representation."""
        for filter_type in EnumCategoryFilter:
            assert str(filter_type) == filter_type.value