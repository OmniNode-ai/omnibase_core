"""
Tests for EnumComplexity enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_complexity import EnumComplexity


class TestEnumComplexity:
    """Test cases for EnumComplexity enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumComplexity.SIMPLE == "simple"
        assert EnumComplexity.MODERATE == "moderate"
        assert EnumComplexity.COMPLEX == "complex"
        assert EnumComplexity.VERY_COMPLEX == "very_complex"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumComplexity, str)
        assert issubclass(EnumComplexity, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        complexity = EnumComplexity.SIMPLE
        assert isinstance(complexity, str)
        assert complexity == "simple"
        assert len(complexity) == 6
        assert complexity.startswith("sim")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumComplexity)
        assert len(values) == 4
        assert EnumComplexity.SIMPLE in values
        assert EnumComplexity.VERY_COMPLEX in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "simple" in EnumComplexity
        assert "invalid_complexity" not in EnumComplexity

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        comp1 = EnumComplexity.SIMPLE
        comp2 = EnumComplexity.COMPLEX

        assert comp1 != comp2
        assert comp1 == "simple"
        assert comp2 == "complex"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        complexity = EnumComplexity.MODERATE
        serialized = complexity.value
        assert serialized == "moderate"

        # Test JSON serialization
        import json

        json_str = json.dumps(complexity)
        assert json_str == '"moderate"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        complexity = EnumComplexity("very_complex")
        assert complexity == EnumComplexity.VERY_COMPLEX

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumComplexity("invalid_complexity")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"simple", "moderate", "complex", "very_complex"}

        actual_values = {member.value for member in EnumComplexity}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Strongly typed complexity levels for operations" in EnumComplexity.__doc__
        )

    def test_enum_str_method(self):
        """Test the __str__ method."""
        complexity = EnumComplexity.SIMPLE
        assert str(complexity) == "simple"
        assert str(EnumComplexity.VERY_COMPLEX) == "very_complex"

    def test_get_estimated_runtime_seconds(self):
        """Test the get_estimated_runtime_seconds class method."""
        assert (
            EnumComplexity.get_estimated_runtime_seconds(EnumComplexity.SIMPLE) == 0.1
        )
        assert (
            EnumComplexity.get_estimated_runtime_seconds(EnumComplexity.MODERATE) == 1.0
        )
        assert (
            EnumComplexity.get_estimated_runtime_seconds(EnumComplexity.COMPLEX) == 10.0
        )
        assert (
            EnumComplexity.get_estimated_runtime_seconds(EnumComplexity.VERY_COMPLEX)
            == 60.0
        )

    def test_requires_monitoring(self):
        """Test the requires_monitoring class method."""
        assert not EnumComplexity.requires_monitoring(EnumComplexity.SIMPLE)
        assert not EnumComplexity.requires_monitoring(EnumComplexity.MODERATE)
        assert EnumComplexity.requires_monitoring(EnumComplexity.COMPLEX)
        assert EnumComplexity.requires_monitoring(EnumComplexity.VERY_COMPLEX)

    def test_allows_parallel_execution(self):
        """Test the allows_parallel_execution class method."""
        assert EnumComplexity.allows_parallel_execution(EnumComplexity.SIMPLE)
        assert EnumComplexity.allows_parallel_execution(EnumComplexity.MODERATE)
        assert not EnumComplexity.allows_parallel_execution(EnumComplexity.COMPLEX)
        assert not EnumComplexity.allows_parallel_execution(EnumComplexity.VERY_COMPLEX)

    def test_enum_complexity_levels(self):
        """Test that enum covers typical complexity levels."""
        # Test basic complexity levels
        assert EnumComplexity.SIMPLE in EnumComplexity
        assert EnumComplexity.MODERATE in EnumComplexity

        # Test advanced complexity levels
        assert EnumComplexity.COMPLEX in EnumComplexity
        assert EnumComplexity.VERY_COMPLEX in EnumComplexity
