# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for EnumCaseStyle enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_case_style import EnumCaseStyle


@pytest.mark.unit
class TestEnumCaseStyle:
    """Test cases for EnumCaseStyle enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumCaseStyle.PASCAL_CASE == "pascal_case"
        assert EnumCaseStyle.SNAKE_CASE == "snake_case"
        assert EnumCaseStyle.CAMEL_CASE == "camel_case"
        assert EnumCaseStyle.KEBAB_CASE == "kebab_case"
        assert EnumCaseStyle.SCREAMING_SNAKE_CASE == "screaming_snake_case"
        assert EnumCaseStyle.ENUM_MEMBER_NAME == "enum_member_name"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumCaseStyle, str)
        assert issubclass(EnumCaseStyle, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        case_style = EnumCaseStyle.SNAKE_CASE
        assert isinstance(case_style, str)
        assert case_style == "snake_case"
        assert len(case_style) == 10
        assert case_style.startswith("snake")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumCaseStyle)
        assert len(values) == 6
        assert EnumCaseStyle.PASCAL_CASE in values
        assert EnumCaseStyle.ENUM_MEMBER_NAME in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "snake_case" in EnumCaseStyle
        assert "invalid_case" not in EnumCaseStyle

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        case1 = EnumCaseStyle.PASCAL_CASE
        case2 = EnumCaseStyle.CAMEL_CASE

        assert case1 != case2
        assert case1 == "pascal_case"
        assert case2 == "camel_case"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        case_style = EnumCaseStyle.KEBAB_CASE
        serialized = case_style.value
        assert serialized == "kebab_case"

        # Test JSON serialization
        import json

        json_str = json.dumps(case_style)
        assert json_str == '"kebab_case"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        case_style = EnumCaseStyle("screaming_snake_case")
        assert case_style == EnumCaseStyle.SCREAMING_SNAKE_CASE

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumCaseStyle("invalid_case")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "pascal_case",
            "snake_case",
            "camel_case",
            "kebab_case",
            "screaming_snake_case",
            "enum_member_name",
        }

        actual_values = {member.value for member in EnumCaseStyle}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Enum for case style types" in EnumCaseStyle.__doc__

    def test_enum_case_styles(self):
        """Test that enum covers typical case styles."""
        # Test common case styles
        assert EnumCaseStyle.PASCAL_CASE in EnumCaseStyle
        assert EnumCaseStyle.SNAKE_CASE in EnumCaseStyle
        assert EnumCaseStyle.CAMEL_CASE in EnumCaseStyle
        assert EnumCaseStyle.KEBAB_CASE in EnumCaseStyle

        # Test special case styles
        assert EnumCaseStyle.SCREAMING_SNAKE_CASE in EnumCaseStyle
        assert EnumCaseStyle.ENUM_MEMBER_NAME in EnumCaseStyle
