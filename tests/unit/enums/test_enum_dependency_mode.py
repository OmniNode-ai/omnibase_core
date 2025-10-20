"""
Tests for EnumDependencyMode enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_dependency_mode import EnumDependencyMode


class TestEnumDependencyMode:
    """Test cases for EnumDependencyMode enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumDependencyMode.REAL == "real"
        assert EnumDependencyMode.MOCK == "mock"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumDependencyMode, str)
        assert issubclass(EnumDependencyMode, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        mode = EnumDependencyMode.REAL
        assert isinstance(mode, str)
        assert mode == "real"
        assert len(mode) == 4
        assert mode.startswith("rea")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumDependencyMode)
        assert len(values) == 2
        assert EnumDependencyMode.REAL in values
        assert EnumDependencyMode.MOCK in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "real" in EnumDependencyMode
        assert "invalid_mode" not in EnumDependencyMode

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        mode1 = EnumDependencyMode.REAL
        mode2 = EnumDependencyMode.MOCK

        assert mode1 != mode2
        assert mode1 == "real"
        assert mode2 == "mock"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        mode = EnumDependencyMode.MOCK
        serialized = mode.value
        assert serialized == "mock"

        # Test JSON serialization
        import json

        json_str = json.dumps(mode)
        assert json_str == '"mock"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        mode = EnumDependencyMode("real")
        assert mode == EnumDependencyMode.REAL

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumDependencyMode("invalid_mode")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"real", "mock"}

        actual_values = {member.value for member in EnumDependencyMode}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Canonical enum for scenario dependency injection modes"
            in EnumDependencyMode.__doc__
        )

    def test_is_real_method(self):
        """Test the is_real method."""
        assert EnumDependencyMode.REAL.is_real()
        assert not EnumDependencyMode.MOCK.is_real()

    def test_is_mock_method(self):
        """Test the is_mock method."""
        assert not EnumDependencyMode.REAL.is_mock()
        assert EnumDependencyMode.MOCK.is_mock()

    def test_enum_dependency_modes(self):
        """Test that enum covers typical dependency modes."""
        # Test real mode
        assert EnumDependencyMode.REAL in EnumDependencyMode

        # Test mock mode
        assert EnumDependencyMode.MOCK in EnumDependencyMode
