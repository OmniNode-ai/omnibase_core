"""
Tests for EnumEventPriority enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_event_priority import EnumEventPriority


@pytest.mark.unit
class TestEnumEventPriority:
    """Test cases for EnumEventPriority enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumEventPriority.CRITICAL == "critical"
        assert EnumEventPriority.HIGH == "high"
        assert EnumEventPriority.NORMAL == "normal"
        assert EnumEventPriority.LOW == "low"
        assert EnumEventPriority.DEFERRED == "deferred"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumEventPriority, str)
        assert issubclass(EnumEventPriority, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        assert str(EnumEventPriority.CRITICAL) == "EnumEventPriority.CRITICAL"
        assert str(EnumEventPriority.HIGH) == "EnumEventPriority.HIGH"
        assert str(EnumEventPriority.NORMAL) == "EnumEventPriority.NORMAL"
        assert str(EnumEventPriority.LOW) == "EnumEventPriority.LOW"
        assert str(EnumEventPriority.DEFERRED) == "EnumEventPriority.DEFERRED"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumEventPriority)
        assert len(values) == 5
        assert EnumEventPriority.CRITICAL in values
        assert EnumEventPriority.HIGH in values
        assert EnumEventPriority.NORMAL in values
        assert EnumEventPriority.LOW in values
        assert EnumEventPriority.DEFERRED in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "critical" in EnumEventPriority
        assert "high" in EnumEventPriority
        assert "normal" in EnumEventPriority
        assert "low" in EnumEventPriority
        assert "deferred" in EnumEventPriority
        assert "invalid" not in EnumEventPriority

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumEventPriority.CRITICAL == "critical"
        assert EnumEventPriority.HIGH == "high"
        assert EnumEventPriority.NORMAL == "normal"
        assert EnumEventPriority.LOW == "low"
        assert EnumEventPriority.DEFERRED == "deferred"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumEventPriority.CRITICAL.value == "critical"
        assert EnumEventPriority.HIGH.value == "high"
        assert EnumEventPriority.NORMAL.value == "normal"
        assert EnumEventPriority.LOW.value == "low"
        assert EnumEventPriority.DEFERRED.value == "deferred"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumEventPriority("critical") == EnumEventPriority.CRITICAL
        assert EnumEventPriority("high") == EnumEventPriority.HIGH
        assert EnumEventPriority("normal") == EnumEventPriority.NORMAL
        assert EnumEventPriority("low") == EnumEventPriority.LOW
        assert EnumEventPriority("deferred") == EnumEventPriority.DEFERRED

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumEventPriority("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [priority.value for priority in EnumEventPriority]
        expected_values = ["critical", "high", "normal", "low", "deferred"]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Priority levels for event processing" in EnumEventPriority.__doc__
