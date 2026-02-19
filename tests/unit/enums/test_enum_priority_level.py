# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumPriorityLevel."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_priority_level import EnumPriorityLevel


@pytest.mark.unit
class TestEnumPriorityLevel:
    """Test suite for EnumPriorityLevel."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumPriorityLevel.CRITICAL == "critical"
        assert EnumPriorityLevel.HIGH == "high"
        assert EnumPriorityLevel.NORMAL == "normal"
        assert EnumPriorityLevel.LOW == "low"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumPriorityLevel, str)
        assert issubclass(EnumPriorityLevel, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        priority = EnumPriorityLevel.HIGH
        assert isinstance(priority, str)
        assert priority == "high"
        assert len(priority) == 4

    def test_enum_str_method(self):
        """Test __str__ method returns value."""
        assert str(EnumPriorityLevel.CRITICAL) == "critical"
        assert str(EnumPriorityLevel.HIGH) == "high"
        assert str(EnumPriorityLevel.NORMAL) == "normal"
        assert str(EnumPriorityLevel.LOW) == "low"

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumPriorityLevel)
        assert len(values) == 4
        assert EnumPriorityLevel.CRITICAL in values
        assert EnumPriorityLevel.LOW in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumPriorityLevel.HIGH in EnumPriorityLevel
        assert "high" in [e.value for e in EnumPriorityLevel]

    def test_enum_comparison(self):
        """Test enum comparison."""
        priority1 = EnumPriorityLevel.NORMAL
        priority2 = EnumPriorityLevel.NORMAL
        priority3 = EnumPriorityLevel.HIGH

        assert priority1 == priority2
        assert priority1 != priority3
        assert priority1 == "normal"

    def test_enum_serialization(self):
        """Test enum serialization."""
        priority = EnumPriorityLevel.CRITICAL
        serialized = priority.value
        assert serialized == "critical"
        json_str = json.dumps(priority)
        assert json_str == '"critical"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        priority = EnumPriorityLevel("high")
        assert priority == EnumPriorityLevel.HIGH

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumPriorityLevel("invalid_priority")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"critical", "high", "normal", "low"}
        actual_values = {e.value for e in EnumPriorityLevel}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumPriorityLevel.__doc__ is not None
        assert "priority" in EnumPriorityLevel.__doc__.lower()

    def test_get_numeric_value(self):
        """Test get_numeric_value method."""
        assert EnumPriorityLevel.LOW.get_numeric_value() == 10
        assert EnumPriorityLevel.NORMAL.get_numeric_value() == 20
        assert EnumPriorityLevel.HIGH.get_numeric_value() == 30
        assert EnumPriorityLevel.CRITICAL.get_numeric_value() == 40

    def test_numeric_value_ordering(self):
        """Test that numeric values maintain proper ordering."""
        values = [
            EnumPriorityLevel.LOW.get_numeric_value(),
            EnumPriorityLevel.NORMAL.get_numeric_value(),
            EnumPriorityLevel.HIGH.get_numeric_value(),
            EnumPriorityLevel.CRITICAL.get_numeric_value(),
        ]
        # Should be in ascending order
        assert values == sorted(values)

    def test_is_high_priority(self):
        """Test is_high_priority method."""
        assert EnumPriorityLevel.CRITICAL.is_high_priority()
        assert EnumPriorityLevel.HIGH.is_high_priority()
        assert not EnumPriorityLevel.NORMAL.is_high_priority()
        assert not EnumPriorityLevel.LOW.is_high_priority()

    def test_requires_immediate_action(self):
        """Test requires_immediate_action method."""
        assert EnumPriorityLevel.CRITICAL.requires_immediate_action()
        assert not EnumPriorityLevel.HIGH.requires_immediate_action()
        assert not EnumPriorityLevel.NORMAL.requires_immediate_action()
        assert not EnumPriorityLevel.LOW.requires_immediate_action()

    def test_priority_less_than(self):
        """Test less than comparison."""
        assert EnumPriorityLevel.LOW < EnumPriorityLevel.NORMAL
        assert EnumPriorityLevel.NORMAL < EnumPriorityLevel.HIGH
        assert EnumPriorityLevel.HIGH < EnumPriorityLevel.CRITICAL

    def test_priority_less_than_or_equal(self):
        """Test less than or equal comparison."""
        assert EnumPriorityLevel.LOW <= EnumPriorityLevel.NORMAL
        assert EnumPriorityLevel.NORMAL <= EnumPriorityLevel.NORMAL
        assert EnumPriorityLevel.HIGH <= EnumPriorityLevel.CRITICAL

    def test_priority_greater_than(self):
        """Test greater than comparison."""
        assert EnumPriorityLevel.CRITICAL > EnumPriorityLevel.HIGH
        assert EnumPriorityLevel.HIGH > EnumPriorityLevel.NORMAL
        assert EnumPriorityLevel.NORMAL > EnumPriorityLevel.LOW

    def test_priority_greater_than_or_equal(self):
        """Test greater than or equal comparison."""
        assert EnumPriorityLevel.CRITICAL >= EnumPriorityLevel.HIGH
        assert EnumPriorityLevel.NORMAL >= EnumPriorityLevel.NORMAL
        assert EnumPriorityLevel.NORMAL >= EnumPriorityLevel.LOW

    def test_priority_sorting(self):
        """Test that priorities can be sorted correctly."""
        priorities = [
            EnumPriorityLevel.HIGH,
            EnumPriorityLevel.LOW,
            EnumPriorityLevel.CRITICAL,
            EnumPriorityLevel.NORMAL,
        ]
        sorted_priorities = sorted(priorities)
        expected = [
            EnumPriorityLevel.LOW,
            EnumPriorityLevel.NORMAL,
            EnumPriorityLevel.HIGH,
            EnumPriorityLevel.CRITICAL,
        ]
        assert sorted_priorities == expected

    def test_priority_comparison_completeness(self):
        """Test that all comparison operators work correctly."""
        low = EnumPriorityLevel.LOW
        high = EnumPriorityLevel.HIGH

        # Comprehensive comparison tests
        assert low < high
        assert low <= high
        assert high > low
        assert high >= low
        assert not (low > high)
        assert not (high < low)
