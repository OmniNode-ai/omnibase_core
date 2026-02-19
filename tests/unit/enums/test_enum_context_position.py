# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for EnumContextPosition enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_context_position import EnumContextPosition


@pytest.mark.unit
class TestEnumContextPosition:
    """Test cases for EnumContextPosition enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumContextPosition.BEFORE == "before"
        assert EnumContextPosition.AFTER == "after"
        assert EnumContextPosition.REPLACE == "replace"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumContextPosition, str)
        assert issubclass(EnumContextPosition, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        position = EnumContextPosition.BEFORE
        assert isinstance(position, str)
        assert position == "before"
        assert len(position) == 6
        assert position.startswith("bef")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumContextPosition)
        assert len(values) == 3
        assert EnumContextPosition.BEFORE in values
        assert EnumContextPosition.REPLACE in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "before" in EnumContextPosition
        assert "invalid_position" not in EnumContextPosition

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        pos1 = EnumContextPosition.BEFORE
        pos2 = EnumContextPosition.AFTER

        assert pos1 != pos2
        assert pos1 == "before"
        assert pos2 == "after"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        position = EnumContextPosition.REPLACE
        serialized = position.value
        assert serialized == "replace"

        # Test JSON serialization
        import json

        json_str = json.dumps(position)
        assert json_str == '"replace"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        position = EnumContextPosition("after")
        assert position == EnumContextPosition.AFTER

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumContextPosition("invalid_position")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"before", "after", "replace"}

        actual_values = {member.value for member in EnumContextPosition}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Context section positions" in EnumContextPosition.__doc__

    def test_enum_context_positions(self):
        """Test that enum covers typical context positions."""
        # Test relative positions
        assert EnumContextPosition.BEFORE in EnumContextPosition
        assert EnumContextPosition.AFTER in EnumContextPosition

        # Test replacement position
        assert EnumContextPosition.REPLACE in EnumContextPosition
