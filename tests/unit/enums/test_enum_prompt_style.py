# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumPromptStyle."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_prompt_style import EnumPromptStyle


@pytest.mark.unit
class TestEnumPromptStyle:
    """Test suite for EnumPromptStyle."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumPromptStyle.PLAIN == "plain"
        assert EnumPromptStyle.MARKDOWN == "markdown"
        assert EnumPromptStyle.XML == "xml"
        assert EnumPromptStyle.JSON_INSTRUCTIONS == "json_instructions"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumPromptStyle, str)
        assert issubclass(EnumPromptStyle, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        style = EnumPromptStyle.MARKDOWN
        assert isinstance(style, str)
        assert style == "markdown"
        assert len(style) == 8

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumPromptStyle)
        assert len(values) == 4
        assert EnumPromptStyle.PLAIN in values
        assert EnumPromptStyle.JSON_INSTRUCTIONS in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumPromptStyle.XML in EnumPromptStyle
        assert "xml" in [e.value for e in EnumPromptStyle]

    def test_enum_comparison(self):
        """Test enum comparison."""
        style1 = EnumPromptStyle.PLAIN
        style2 = EnumPromptStyle.PLAIN
        style3 = EnumPromptStyle.MARKDOWN

        assert style1 == style2
        assert style1 != style3
        assert style1 == "plain"

    def test_enum_serialization(self):
        """Test enum serialization."""
        style = EnumPromptStyle.XML
        serialized = style.value
        assert serialized == "xml"
        json_str = json.dumps(style)
        assert json_str == '"xml"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        style = EnumPromptStyle("markdown")
        assert style == EnumPromptStyle.MARKDOWN

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumPromptStyle("invalid_style")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"plain", "markdown", "xml", "json_instructions"}
        actual_values = {e.value for e in EnumPromptStyle}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumPromptStyle.__doc__ is not None
        assert "prompt" in EnumPromptStyle.__doc__.lower()

    def test_text_format_styles(self):
        """Test text-based formatting styles."""
        text_styles = {
            EnumPromptStyle.PLAIN,
            EnumPromptStyle.MARKDOWN,
        }
        assert all(style in EnumPromptStyle for style in text_styles)

    def test_structured_format_styles(self):
        """Test structured formatting styles."""
        structured_styles = {
            EnumPromptStyle.XML,
            EnumPromptStyle.JSON_INSTRUCTIONS,
        }
        assert all(style in EnumPromptStyle for style in structured_styles)

    def test_all_styles_categorized(self):
        """Test that all styles can be categorized."""
        # Text formats
        text_formats = {
            EnumPromptStyle.PLAIN,
            EnumPromptStyle.MARKDOWN,
        }

        # Structured formats
        structured_formats = {
            EnumPromptStyle.XML,
            EnumPromptStyle.JSON_INSTRUCTIONS,
        }

        # All styles should be categorized
        all_styles = text_formats | structured_formats
        assert all_styles == set(EnumPromptStyle)

    def test_style_naming_convention(self):
        """Test that style values follow naming conventions."""
        for style in EnumPromptStyle:
            # Should be lowercase with underscores
            assert style.value == style.value.lower()
            assert "-" not in style.value  # No hyphens
