"""
Tests for EnumIntelligencePriorityLevel enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_intelligence_priority_level import (
    EnumIntelligencePriorityLevel,
)


@pytest.mark.unit
class TestEnumIntelligencePriorityLevel:
    """Test cases for EnumIntelligencePriorityLevel enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumIntelligencePriorityLevel.LOW == "low"
        assert EnumIntelligencePriorityLevel.NORMAL == "normal"
        assert EnumIntelligencePriorityLevel.HIGH == "high"
        assert EnumIntelligencePriorityLevel.CRITICAL == "critical"
        assert EnumIntelligencePriorityLevel.EMERGENCY == "emergency"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumIntelligencePriorityLevel, str)
        assert issubclass(EnumIntelligencePriorityLevel, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values (StrValueHelper returns value)."""
        assert str(EnumIntelligencePriorityLevel.LOW) == "low"
        assert str(EnumIntelligencePriorityLevel.NORMAL) == "normal"
        assert str(EnumIntelligencePriorityLevel.HIGH) == "high"
        assert str(EnumIntelligencePriorityLevel.CRITICAL) == "critical"
        assert str(EnumIntelligencePriorityLevel.EMERGENCY) == "emergency"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumIntelligencePriorityLevel)
        assert len(values) == 5
        assert EnumIntelligencePriorityLevel.LOW in values
        assert EnumIntelligencePriorityLevel.NORMAL in values
        assert EnumIntelligencePriorityLevel.HIGH in values
        assert EnumIntelligencePriorityLevel.CRITICAL in values
        assert EnumIntelligencePriorityLevel.EMERGENCY in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "low" in EnumIntelligencePriorityLevel
        assert "normal" in EnumIntelligencePriorityLevel
        assert "high" in EnumIntelligencePriorityLevel
        assert "critical" in EnumIntelligencePriorityLevel
        assert "emergency" in EnumIntelligencePriorityLevel
        assert "invalid" not in EnumIntelligencePriorityLevel

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumIntelligencePriorityLevel.LOW == "low"
        assert EnumIntelligencePriorityLevel.NORMAL == "normal"
        assert EnumIntelligencePriorityLevel.HIGH == "high"
        assert EnumIntelligencePriorityLevel.CRITICAL == "critical"
        assert EnumIntelligencePriorityLevel.EMERGENCY == "emergency"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumIntelligencePriorityLevel.LOW.value == "low"
        assert EnumIntelligencePriorityLevel.NORMAL.value == "normal"
        assert EnumIntelligencePriorityLevel.HIGH.value == "high"
        assert EnumIntelligencePriorityLevel.CRITICAL.value == "critical"
        assert EnumIntelligencePriorityLevel.EMERGENCY.value == "emergency"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumIntelligencePriorityLevel("low") == EnumIntelligencePriorityLevel.LOW
        assert (
            EnumIntelligencePriorityLevel("normal")
            == EnumIntelligencePriorityLevel.NORMAL
        )
        assert (
            EnumIntelligencePriorityLevel("high") == EnumIntelligencePriorityLevel.HIGH
        )
        assert (
            EnumIntelligencePriorityLevel("critical")
            == EnumIntelligencePriorityLevel.CRITICAL
        )
        assert (
            EnumIntelligencePriorityLevel("emergency")
            == EnumIntelligencePriorityLevel.EMERGENCY
        )

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumIntelligencePriorityLevel("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [level.value for level in EnumIntelligencePriorityLevel]
        expected_values = ["low", "normal", "high", "critical", "emergency"]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Enum for intelligence priority levels with validation"
            in EnumIntelligencePriorityLevel.__doc__
        )

    def test_priority_hierarchy(self):
        """Test that priority levels follow expected hierarchy."""
        # Emergency should be highest priority
        assert EnumIntelligencePriorityLevel.EMERGENCY in EnumIntelligencePriorityLevel
        # Critical should be high priority
        assert EnumIntelligencePriorityLevel.CRITICAL in EnumIntelligencePriorityLevel
        # High should be above normal
        assert EnumIntelligencePriorityLevel.HIGH in EnumIntelligencePriorityLevel
        # Normal should be standard priority
        assert EnumIntelligencePriorityLevel.NORMAL in EnumIntelligencePriorityLevel
        # Low should be lowest priority
        assert EnumIntelligencePriorityLevel.LOW in EnumIntelligencePriorityLevel
