"""
Tests for EnumContentType enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_content_type import EnumContentType


@pytest.mark.unit
class TestEnumContentType:
    """Test cases for EnumContentType enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumContentType.TEXT == "text"
        assert EnumContentType.IMAGE == "image"
        assert EnumContentType.TOOL_USE == "tool_use"
        assert EnumContentType.TOOL_RESULT == "tool_result"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumContentType, str)
        assert issubclass(EnumContentType, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        content_type = EnumContentType.TEXT
        assert isinstance(content_type, str)
        assert content_type == "text"
        assert len(content_type) == 4
        assert content_type.startswith("tex")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumContentType)
        assert len(values) == 4
        assert EnumContentType.TEXT in values
        assert EnumContentType.TOOL_RESULT in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "text" in EnumContentType
        assert "invalid_type" not in EnumContentType

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        type1 = EnumContentType.TEXT
        type2 = EnumContentType.IMAGE

        assert type1 != type2
        assert type1 == "text"
        assert type2 == "image"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        content_type = EnumContentType.TOOL_USE
        serialized = content_type.value
        assert serialized == "tool_use"

        # Test JSON serialization
        import json

        json_str = json.dumps(content_type)
        assert json_str == '"tool_use"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        content_type = EnumContentType("tool_result")
        assert content_type == EnumContentType.TOOL_RESULT

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumContentType("invalid_type")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"text", "image", "tool_use", "tool_result"}

        actual_values = {member.value for member in EnumContentType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Content types in messages" in EnumContentType.__doc__

    def test_enum_content_types(self):
        """Test that enum covers typical content types."""
        # Test basic content types
        assert EnumContentType.TEXT in EnumContentType
        assert EnumContentType.IMAGE in EnumContentType

        # Test tool-related content types
        assert EnumContentType.TOOL_USE in EnumContentType
        assert EnumContentType.TOOL_RESULT in EnumContentType
