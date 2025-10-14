"""Tests for EnumRequestField."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_request_field import EnumRequestField


class TestEnumRequestField:
    """Test suite for EnumRequestField."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumRequestField.MODEL == "model"
        assert EnumRequestField.SYSTEM == "system"
        assert EnumRequestField.MESSAGES == "messages"
        assert EnumRequestField.TOOLS == "tools"
        assert EnumRequestField.MAX_TOKENS == "max_tokens"
        assert EnumRequestField.TEMPERATURE == "temperature"
        assert EnumRequestField.CONTENT == "content"
        assert EnumRequestField.ROLE == "role"
        assert EnumRequestField.TYPE == "type"
        assert EnumRequestField.TEXT == "text"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumRequestField, str)
        assert issubclass(EnumRequestField, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        field = EnumRequestField.MODEL
        assert isinstance(field, str)
        assert field == "model"
        assert len(field) == 5

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumRequestField)
        assert len(values) == 10
        assert EnumRequestField.MODEL in values
        assert EnumRequestField.TEXT in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumRequestField.MESSAGES in EnumRequestField
        assert "messages" in [e.value for e in EnumRequestField]

    def test_enum_comparison(self):
        """Test enum comparison."""
        field1 = EnumRequestField.TEMPERATURE
        field2 = EnumRequestField.TEMPERATURE
        field3 = EnumRequestField.MAX_TOKENS

        assert field1 == field2
        assert field1 != field3
        assert field1 == "temperature"

    def test_enum_serialization(self):
        """Test enum serialization."""
        field = EnumRequestField.TOOLS
        serialized = field.value
        assert serialized == "tools"
        json_str = json.dumps(field)
        assert json_str == '"tools"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        field = EnumRequestField("system")
        assert field == EnumRequestField.SYSTEM

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumRequestField("invalid_field")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "model",
            "system",
            "messages",
            "tools",
            "max_tokens",
            "temperature",
            "content",
            "role",
            "type",
            "text",
        }
        actual_values = {e.value for e in EnumRequestField}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumRequestField.__doc__ is not None
        assert "request" in EnumRequestField.__doc__.lower()

    def test_top_level_fields(self):
        """Test top-level request fields."""
        top_level = {
            EnumRequestField.MODEL,
            EnumRequestField.SYSTEM,
            EnumRequestField.MESSAGES,
            EnumRequestField.TOOLS,
            EnumRequestField.MAX_TOKENS,
            EnumRequestField.TEMPERATURE,
        }
        assert all(field in EnumRequestField for field in top_level)

    def test_nested_fields(self):
        """Test nested request fields."""
        nested = {
            EnumRequestField.CONTENT,
            EnumRequestField.ROLE,
            EnumRequestField.TYPE,
            EnumRequestField.TEXT,
        }
        assert all(field in EnumRequestField for field in nested)

    def test_all_fields_categorized(self):
        """Test that all fields are properly categorized."""
        # Top-level configuration fields
        config_fields = {
            EnumRequestField.MODEL,
            EnumRequestField.SYSTEM,
            EnumRequestField.MESSAGES,
            EnumRequestField.TOOLS,
            EnumRequestField.MAX_TOKENS,
            EnumRequestField.TEMPERATURE,
        }
        # Message/content structure fields
        structure_fields = {
            EnumRequestField.CONTENT,
            EnumRequestField.ROLE,
            EnumRequestField.TYPE,
            EnumRequestField.TEXT,
        }
        all_fields = config_fields | structure_fields
        assert all_fields == set(EnumRequestField)
