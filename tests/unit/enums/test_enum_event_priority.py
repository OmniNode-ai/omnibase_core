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
        assert EnumEventPriority.CRITICAL == "CRITICAL"
        assert EnumEventPriority.HIGH == "HIGH"
        assert EnumEventPriority.NORMAL == "NORMAL"
        assert EnumEventPriority.LOW == "LOW"
        assert EnumEventPriority.DEFERRED == "DEFERRED"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumEventPriority, str)
        assert issubclass(EnumEventPriority, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values (str() returns value due to StrValueHelper mixin)."""
        assert str(EnumEventPriority.CRITICAL) == "CRITICAL"
        assert str(EnumEventPriority.HIGH) == "HIGH"
        assert str(EnumEventPriority.NORMAL) == "NORMAL"
        assert str(EnumEventPriority.LOW) == "LOW"
        assert str(EnumEventPriority.DEFERRED) == "DEFERRED"

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
        assert "CRITICAL" in EnumEventPriority
        assert "HIGH" in EnumEventPriority
        assert "NORMAL" in EnumEventPriority
        assert "LOW" in EnumEventPriority
        assert "DEFERRED" in EnumEventPriority
        assert "invalid" not in EnumEventPriority

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumEventPriority.CRITICAL == "CRITICAL"
        assert EnumEventPriority.HIGH == "HIGH"
        assert EnumEventPriority.NORMAL == "NORMAL"
        assert EnumEventPriority.LOW == "LOW"
        assert EnumEventPriority.DEFERRED == "DEFERRED"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumEventPriority.CRITICAL.value == "CRITICAL"
        assert EnumEventPriority.HIGH.value == "HIGH"
        assert EnumEventPriority.NORMAL.value == "NORMAL"
        assert EnumEventPriority.LOW.value == "LOW"
        assert EnumEventPriority.DEFERRED.value == "DEFERRED"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumEventPriority("CRITICAL") == EnumEventPriority.CRITICAL
        assert EnumEventPriority("HIGH") == EnumEventPriority.HIGH
        assert EnumEventPriority("NORMAL") == EnumEventPriority.NORMAL
        assert EnumEventPriority("LOW") == EnumEventPriority.LOW
        assert EnumEventPriority("DEFERRED") == EnumEventPriority.DEFERRED

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumEventPriority("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [priority.value for priority in EnumEventPriority]
        expected_values = ["CRITICAL", "HIGH", "NORMAL", "LOW", "DEFERRED"]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Priority levels for event processing" in EnumEventPriority.__doc__
