"""Tests for EnumResponseFormat."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_response_format import EnumResponseFormat


@pytest.mark.unit
class TestEnumResponseFormat:
    """Test suite for EnumResponseFormat."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumResponseFormat.TEXT == "text"
        assert EnumResponseFormat.JSON == "json"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumResponseFormat, str)
        assert issubclass(EnumResponseFormat, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        format_ = EnumResponseFormat.TEXT
        assert isinstance(format_, str)
        assert format_ == "text"
        assert len(format_) == 4

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumResponseFormat)
        assert len(values) == 2
        assert EnumResponseFormat.TEXT in values
        assert EnumResponseFormat.JSON in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumResponseFormat.JSON in EnumResponseFormat
        assert "json" in [e.value for e in EnumResponseFormat]

    def test_enum_comparison(self):
        """Test enum comparison."""
        format1 = EnumResponseFormat.TEXT
        format2 = EnumResponseFormat.TEXT
        format3 = EnumResponseFormat.JSON

        assert format1 == format2
        assert format1 != format3
        assert format1 == "text"

    def test_enum_serialization(self):
        """Test enum serialization."""
        format_ = EnumResponseFormat.JSON
        serialized = format_.value
        assert serialized == "json"
        json_str = json.dumps(format_)
        assert json_str == '"json"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        format_ = EnumResponseFormat("text")
        assert format_ == EnumResponseFormat.TEXT

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumResponseFormat("invalid_format")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"text", "json"}
        actual_values = {e.value for e in EnumResponseFormat}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumResponseFormat.__doc__ is not None
        assert "response" in EnumResponseFormat.__doc__.lower()

    def test_format_categorization(self):
        """Test format categorization."""
        # Unstructured format
        unstructured = {EnumResponseFormat.TEXT}
        # Structured format
        structured = {EnumResponseFormat.JSON}

        assert all(f in EnumResponseFormat for f in unstructured)
        assert all(f in EnumResponseFormat for f in structured)
        assert unstructured | structured == set(EnumResponseFormat)
