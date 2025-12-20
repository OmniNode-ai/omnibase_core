"""
Tests for EnumDeliveryMode enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_delivery_mode import EnumDeliveryMode


@pytest.mark.unit
class TestEnumDeliveryMode:
    """Test cases for EnumDeliveryMode enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumDeliveryMode.DIRECT == "direct"
        assert EnumDeliveryMode.INMEMORY == "inmemory"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumDeliveryMode, str)
        assert issubclass(EnumDeliveryMode, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        mode = EnumDeliveryMode.DIRECT
        assert isinstance(mode, str)
        assert mode == "direct"
        assert len(mode) == 6
        assert mode.startswith("dir")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumDeliveryMode)
        assert len(values) == 2
        assert EnumDeliveryMode.DIRECT in values
        assert EnumDeliveryMode.INMEMORY in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "direct" in EnumDeliveryMode
        assert "invalid_mode" not in EnumDeliveryMode

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        mode1 = EnumDeliveryMode.DIRECT
        mode2 = EnumDeliveryMode.INMEMORY

        assert mode1 != mode2
        assert mode1 == "direct"
        assert mode2 == "inmemory"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        mode = EnumDeliveryMode.INMEMORY
        serialized = mode.value
        assert serialized == "inmemory"

        # Test JSON serialization
        import json

        json_str = json.dumps(mode)
        assert json_str == '"inmemory"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        mode = EnumDeliveryMode("direct")
        assert mode == EnumDeliveryMode.DIRECT

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumDeliveryMode("invalid_mode")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"direct", "inmemory"}

        actual_values = {member.value for member in EnumDeliveryMode}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Enumeration of event delivery modes" in EnumDeliveryMode.__doc__

    def test_enum_delivery_modes(self):
        """Test that enum covers typical delivery modes."""
        # Test direct delivery
        assert EnumDeliveryMode.DIRECT in EnumDeliveryMode

        # Test in-memory delivery
        assert EnumDeliveryMode.INMEMORY in EnumDeliveryMode
