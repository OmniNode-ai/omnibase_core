"""
Tests for EnumComparisonOperators enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_comparison_operators import EnumComparisonOperators


@pytest.mark.unit
class TestEnumComparisonOperators:
    """Test cases for EnumComparisonOperators enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumComparisonOperators.EQUALS == "equals"
        assert EnumComparisonOperators.NOT_EQUALS == "not_equals"
        assert EnumComparisonOperators.GREATER_THAN == "greater_than"
        assert EnumComparisonOperators.LESS_THAN == "less_than"
        assert EnumComparisonOperators.GREATER_THAN_OR_EQUAL == "greater_than_or_equal"
        assert EnumComparisonOperators.LESS_THAN_OR_EQUAL == "less_than_or_equal"
        assert EnumComparisonOperators.CONTAINS == "contains"
        assert EnumComparisonOperators.NOT_CONTAINS == "not_contains"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumComparisonOperators, str)
        assert issubclass(EnumComparisonOperators, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        operator = EnumComparisonOperators.EQUALS
        assert isinstance(operator, str)
        assert operator == "equals"
        assert len(operator) == 6
        assert operator.startswith("equal")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumComparisonOperators)
        assert len(values) == 8
        assert EnumComparisonOperators.EQUALS in values
        assert EnumComparisonOperators.NOT_CONTAINS in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "equals" in EnumComparisonOperators
        assert "invalid_operator" not in EnumComparisonOperators

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        op1 = EnumComparisonOperators.EQUALS
        op2 = EnumComparisonOperators.NOT_EQUALS

        assert op1 != op2
        assert op1 == "equals"
        assert op2 == "not_equals"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        operator = EnumComparisonOperators.GREATER_THAN
        serialized = operator.value
        assert serialized == "greater_than"

        # Test JSON serialization
        import json

        json_str = json.dumps(operator)
        assert json_str == '"greater_than"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        operator = EnumComparisonOperators("less_than")
        assert operator == EnumComparisonOperators.LESS_THAN

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumComparisonOperators("invalid_operator")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "equals",
            "not_equals",
            "greater_than",
            "less_than",
            "greater_than_or_equal",
            "less_than_or_equal",
            "contains",
            "not_contains",
        }

        actual_values = {member.value for member in EnumComparisonOperators}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Enum for comparison operators used in conditional logic"
            in EnumComparisonOperators.__doc__
        )

    def test_enum_comparison_operators(self):
        """Test that enum covers typical comparison operators."""
        # Test equality operators
        assert EnumComparisonOperators.EQUALS in EnumComparisonOperators
        assert EnumComparisonOperators.NOT_EQUALS in EnumComparisonOperators

        # Test relational operators
        assert EnumComparisonOperators.GREATER_THAN in EnumComparisonOperators
        assert EnumComparisonOperators.LESS_THAN in EnumComparisonOperators
        assert EnumComparisonOperators.GREATER_THAN_OR_EQUAL in EnumComparisonOperators
        assert EnumComparisonOperators.LESS_THAN_OR_EQUAL in EnumComparisonOperators

        # Test containment operators
        assert EnumComparisonOperators.CONTAINS in EnumComparisonOperators
        assert EnumComparisonOperators.NOT_CONTAINS in EnumComparisonOperators
