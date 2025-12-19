"""
Tests for EnumHandlerPriority enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_handler_priority import EnumHandlerPriority


@pytest.mark.unit
class TestEnumHandlerPriority:
    """Test cases for EnumHandlerPriority enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumHandlerPriority.CORE == 100
        assert EnumHandlerPriority.RUNTIME == 50
        assert EnumHandlerPriority.NODE_LOCAL == 10
        assert EnumHandlerPriority.PLUGIN == 0
        assert EnumHandlerPriority.CUSTOM == 25
        assert EnumHandlerPriority.CONTRACT == 75
        assert EnumHandlerPriority.LOW == 0
        assert EnumHandlerPriority.HIGH == 100
        assert EnumHandlerPriority.TEST == 5

    def test_enum_inheritance(self):
        """Test that enum inherits from int and Enum."""
        assert issubclass(EnumHandlerPriority, int)
        assert issubclass(EnumHandlerPriority, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        assert str(EnumHandlerPriority.CORE) == "EnumHandlerPriority.CORE"
        assert str(EnumHandlerPriority.RUNTIME) == "EnumHandlerPriority.RUNTIME"
        assert str(EnumHandlerPriority.NODE_LOCAL) == "EnumHandlerPriority.NODE_LOCAL"
        assert str(EnumHandlerPriority.PLUGIN) == "EnumHandlerPriority.PLUGIN"
        assert str(EnumHandlerPriority.CUSTOM) == "EnumHandlerPriority.CUSTOM"
        assert str(EnumHandlerPriority.CONTRACT) == "EnumHandlerPriority.CONTRACT"
        # LOW and HIGH are aliases for PLUGIN and CORE respectively
        assert str(EnumHandlerPriority.LOW) == "EnumHandlerPriority.PLUGIN"
        assert str(EnumHandlerPriority.HIGH) == "EnumHandlerPriority.CORE"
        assert str(EnumHandlerPriority.TEST) == "EnumHandlerPriority.TEST"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumHandlerPriority)
        assert len(values) == 7  # Duplicate values are not included
        assert EnumHandlerPriority.CORE in values
        assert EnumHandlerPriority.RUNTIME in values
        assert EnumHandlerPriority.NODE_LOCAL in values
        assert EnumHandlerPriority.PLUGIN in values
        assert EnumHandlerPriority.CUSTOM in values
        assert EnumHandlerPriority.CONTRACT in values
        assert EnumHandlerPriority.LOW in values
        assert EnumHandlerPriority.HIGH in values
        assert EnumHandlerPriority.TEST in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert 100 in EnumHandlerPriority
        assert 50 in EnumHandlerPriority
        assert 10 in EnumHandlerPriority
        assert 0 in EnumHandlerPriority
        assert 25 in EnumHandlerPriority
        assert 75 in EnumHandlerPriority
        assert 5 in EnumHandlerPriority
        assert 999 not in EnumHandlerPriority

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumHandlerPriority.CORE == 100
        assert EnumHandlerPriority.RUNTIME == 50
        assert EnumHandlerPriority.NODE_LOCAL == 10
        assert EnumHandlerPriority.PLUGIN == 0
        assert EnumHandlerPriority.CUSTOM == 25
        assert EnumHandlerPriority.CONTRACT == 75
        assert EnumHandlerPriority.LOW == 0
        assert EnumHandlerPriority.HIGH == 100
        assert EnumHandlerPriority.TEST == 5

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumHandlerPriority.CORE.value == 100
        assert EnumHandlerPriority.RUNTIME.value == 50
        assert EnumHandlerPriority.NODE_LOCAL.value == 10
        assert EnumHandlerPriority.PLUGIN.value == 0
        assert EnumHandlerPriority.CUSTOM.value == 25
        assert EnumHandlerPriority.CONTRACT.value == 75
        assert EnumHandlerPriority.LOW.value == 0
        assert EnumHandlerPriority.HIGH.value == 100
        assert EnumHandlerPriority.TEST.value == 5

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumHandlerPriority(100) == EnumHandlerPriority.CORE
        assert EnumHandlerPriority(50) == EnumHandlerPriority.RUNTIME
        assert EnumHandlerPriority(10) == EnumHandlerPriority.NODE_LOCAL
        assert EnumHandlerPriority(0) == EnumHandlerPriority.PLUGIN
        assert EnumHandlerPriority(25) == EnumHandlerPriority.CUSTOM
        assert EnumHandlerPriority(75) == EnumHandlerPriority.CONTRACT
        assert EnumHandlerPriority(5) == EnumHandlerPriority.TEST

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumHandlerPriority(999)

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [priority.value for priority in EnumHandlerPriority]
        expected_values = [100, 50, 10, 0, 25, 75, 5]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Canonical priority levels for file type handlers"
            in EnumHandlerPriority.__doc__
        )

    def test_priority_ordering(self):
        """Test that priority values are ordered correctly."""
        assert EnumHandlerPriority.CORE > EnumHandlerPriority.CONTRACT
        assert EnumHandlerPriority.CONTRACT > EnumHandlerPriority.RUNTIME
        assert EnumHandlerPriority.RUNTIME > EnumHandlerPriority.CUSTOM
        assert EnumHandlerPriority.CUSTOM > EnumHandlerPriority.NODE_LOCAL
        assert EnumHandlerPriority.NODE_LOCAL > EnumHandlerPriority.TEST
        assert EnumHandlerPriority.TEST > EnumHandlerPriority.PLUGIN

    def test_duplicate_values(self):
        """Test that duplicate values are handled correctly."""
        # Both CORE and HIGH have value 100
        assert EnumHandlerPriority.CORE == EnumHandlerPriority.HIGH
        # Both PLUGIN and LOW have value 0
        assert EnumHandlerPriority.PLUGIN == EnumHandlerPriority.LOW
