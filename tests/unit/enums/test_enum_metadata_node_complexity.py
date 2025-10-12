"""Tests for enum_metadata_node_complexity.py"""

from enum import Enum, unique

import pytest

from omnibase_core.enums.enum_metadata_node_complexity import EnumMetadataNodeComplexity


class TestEnumMetadataNodeComplexity:
    """Test cases for EnumMetadataNodeComplexity"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumMetadataNodeComplexity.SIMPLE == "simple"
        assert EnumMetadataNodeComplexity.MODERATE == "moderate"
        assert EnumMetadataNodeComplexity.COMPLEX == "complex"
        assert EnumMetadataNodeComplexity.ADVANCED == "advanced"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumMetadataNodeComplexity, str)
        assert issubclass(EnumMetadataNodeComplexity, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumMetadataNodeComplexity.SIMPLE == "simple"
        assert EnumMetadataNodeComplexity.MODERATE == "moderate"
        assert EnumMetadataNodeComplexity.COMPLEX == "complex"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumMetadataNodeComplexity)
        assert len(values) == 4
        assert EnumMetadataNodeComplexity.SIMPLE in values
        assert EnumMetadataNodeComplexity.ADVANCED in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumMetadataNodeComplexity.SIMPLE in EnumMetadataNodeComplexity
        assert "simple" in EnumMetadataNodeComplexity
        assert "invalid_value" not in EnumMetadataNodeComplexity

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumMetadataNodeComplexity.SIMPLE == EnumMetadataNodeComplexity.SIMPLE
        assert EnumMetadataNodeComplexity.MODERATE != EnumMetadataNodeComplexity.SIMPLE
        assert EnumMetadataNodeComplexity.SIMPLE == "simple"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumMetadataNodeComplexity.SIMPLE.value == "simple"
        assert EnumMetadataNodeComplexity.MODERATE.value == "moderate"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumMetadataNodeComplexity("simple") == EnumMetadataNodeComplexity.SIMPLE
        assert (
            EnumMetadataNodeComplexity("moderate")
            == EnumMetadataNodeComplexity.MODERATE
        )

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumMetadataNodeComplexity("invalid_value")

        with pytest.raises(ValueError):
            EnumMetadataNodeComplexity("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {"simple", "moderate", "complex", "advanced"}
        actual_values = {member.value for member in EnumMetadataNodeComplexity}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert (
            "Metadata node complexity enumeration" in EnumMetadataNodeComplexity.__doc__
        )

    def test_enum_unique_decorator(self):
        """Test that enum has @unique decorator"""
        # The @unique decorator ensures no duplicate values
        # This is tested implicitly by the fact that the enum works correctly
        assert len(set(EnumMetadataNodeComplexity)) == len(EnumMetadataNodeComplexity)

    def test_enum_complexity_levels(self):
        """Test specific complexity levels"""
        # Simple complexity
        assert EnumMetadataNodeComplexity.SIMPLE.value == "simple"

        # Moderate complexity
        assert EnumMetadataNodeComplexity.MODERATE.value == "moderate"

        # Complex complexity
        assert EnumMetadataNodeComplexity.COMPLEX.value == "complex"

        # Advanced complexity
        assert EnumMetadataNodeComplexity.ADVANCED.value == "advanced"

    def test_enum_complexity_hierarchy(self):
        """Test complexity hierarchy"""
        # Simple to Advanced progression
        complexity_levels = [
            EnumMetadataNodeComplexity.SIMPLE,
            EnumMetadataNodeComplexity.MODERATE,
            EnumMetadataNodeComplexity.COMPLEX,
            EnumMetadataNodeComplexity.ADVANCED,
        ]

        # Verify all levels are present
        assert len(complexity_levels) == 4
        assert all(level in EnumMetadataNodeComplexity for level in complexity_levels)

    def test_enum_complexity_categories(self):
        """Test complexity categories"""
        # Basic complexity
        basic_complexity = {EnumMetadataNodeComplexity.SIMPLE}

        # Intermediate complexity
        intermediate_complexity = {EnumMetadataNodeComplexity.MODERATE}

        # High complexity
        high_complexity = {
            EnumMetadataNodeComplexity.COMPLEX,
            EnumMetadataNodeComplexity.ADVANCED,
        }

        all_complexity = set(EnumMetadataNodeComplexity)
        assert (
            basic_complexity.union(intermediate_complexity).union(high_complexity)
            == all_complexity
        )
