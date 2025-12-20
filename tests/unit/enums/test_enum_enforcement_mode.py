"""
Tests for EnumEnforcementMode enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_enforcement_mode import EnumEnforcementMode


@pytest.mark.unit
class TestEnumEnforcementMode:
    """Test cases for EnumEnforcementMode enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumEnforcementMode.HARD == "hard"
        assert EnumEnforcementMode.SOFT == "soft"
        assert EnumEnforcementMode.ADVISORY == "advisory"
        assert EnumEnforcementMode.DISABLED == "disabled"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumEnforcementMode, str)
        assert issubclass(EnumEnforcementMode, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        assert str(EnumEnforcementMode.HARD) == "hard"
        assert str(EnumEnforcementMode.SOFT) == "soft"
        assert str(EnumEnforcementMode.ADVISORY) == "advisory"
        assert str(EnumEnforcementMode.DISABLED) == "disabled"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumEnforcementMode)
        assert len(values) == 4
        assert EnumEnforcementMode.HARD in values
        assert EnumEnforcementMode.SOFT in values
        assert EnumEnforcementMode.ADVISORY in values
        assert EnumEnforcementMode.DISABLED in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "hard" in EnumEnforcementMode
        assert "soft" in EnumEnforcementMode
        assert "advisory" in EnumEnforcementMode
        assert "disabled" in EnumEnforcementMode
        assert "invalid" not in EnumEnforcementMode

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumEnforcementMode.HARD == "hard"
        assert EnumEnforcementMode.SOFT == "soft"
        assert EnumEnforcementMode.ADVISORY == "advisory"
        assert EnumEnforcementMode.DISABLED == "disabled"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumEnforcementMode.HARD.value == "hard"
        assert EnumEnforcementMode.SOFT.value == "soft"
        assert EnumEnforcementMode.ADVISORY.value == "advisory"
        assert EnumEnforcementMode.DISABLED.value == "disabled"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumEnforcementMode("hard") == EnumEnforcementMode.HARD
        assert EnumEnforcementMode("soft") == EnumEnforcementMode.SOFT
        assert EnumEnforcementMode("advisory") == EnumEnforcementMode.ADVISORY
        assert EnumEnforcementMode("disabled") == EnumEnforcementMode.DISABLED

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumEnforcementMode("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [mode.value for mode in EnumEnforcementMode]
        expected_values = ["hard", "soft", "advisory", "disabled"]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Enforcement strategy modes" in EnumEnforcementMode.__doc__

    def test_is_blocking_method(self):
        """Test the is_blocking method."""
        assert EnumEnforcementMode.HARD.is_blocking() is True
        assert EnumEnforcementMode.SOFT.is_blocking() is False
        assert EnumEnforcementMode.ADVISORY.is_blocking() is False
        assert EnumEnforcementMode.DISABLED.is_blocking() is False

    def test_allows_overrun_method(self):
        """Test the allows_overrun method."""
        assert EnumEnforcementMode.HARD.allows_overrun() is False
        assert EnumEnforcementMode.SOFT.allows_overrun() is True
        assert EnumEnforcementMode.ADVISORY.allows_overrun() is True
        assert EnumEnforcementMode.DISABLED.allows_overrun() is False

    def test_provides_warnings_method(self):
        """Test the provides_warnings method."""
        assert EnumEnforcementMode.HARD.provides_warnings() is False
        assert EnumEnforcementMode.SOFT.provides_warnings() is True
        assert EnumEnforcementMode.ADVISORY.provides_warnings() is True
        assert EnumEnforcementMode.DISABLED.provides_warnings() is False
