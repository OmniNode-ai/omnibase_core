"""Tests for EnumOutputMode."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_output_mode import EnumOutputMode


class TestEnumOutputMode:
    """Test suite for EnumOutputMode."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumOutputMode.CONTENT == "content"
        assert EnumOutputMode.FILES_WITH_MATCHES == "files_with_matches"
        assert EnumOutputMode.COUNT == "count"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumOutputMode, str)
        assert issubclass(EnumOutputMode, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        mode = EnumOutputMode.CONTENT
        assert isinstance(mode, str)
        assert mode == "content"
        assert len(mode) == 7
        assert mode.startswith("cont")

    def test_enum_str_method(self):
        """Test __str__ method returns value."""
        assert str(EnumOutputMode.CONTENT) == "content"
        assert str(EnumOutputMode.FILES_WITH_MATCHES) == "files_with_matches"
        assert str(EnumOutputMode.COUNT) == "count"

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumOutputMode)
        assert len(values) == 3
        assert EnumOutputMode.CONTENT in values
        assert EnumOutputMode.FILES_WITH_MATCHES in values
        assert EnumOutputMode.COUNT in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumOutputMode.CONTENT in EnumOutputMode
        assert "content" in [e.value for e in EnumOutputMode]

    def test_enum_comparison(self):
        """Test enum comparison."""
        mode1 = EnumOutputMode.CONTENT
        mode2 = EnumOutputMode.CONTENT
        mode3 = EnumOutputMode.COUNT

        assert mode1 == mode2
        assert mode1 != mode3
        assert mode1 == "content"

    def test_enum_serialization(self):
        """Test enum serialization."""
        mode = EnumOutputMode.FILES_WITH_MATCHES
        serialized = mode.value
        assert serialized == "files_with_matches"
        json_str = json.dumps(mode)
        assert json_str == '"files_with_matches"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        mode = EnumOutputMode("content")
        assert mode == EnumOutputMode.CONTENT

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumOutputMode("invalid_mode")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"content", "files_with_matches", "count"}
        actual_values = {e.value for e in EnumOutputMode}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumOutputMode.__doc__ is not None
        assert "output mode" in EnumOutputMode.__doc__.lower()

    def test_returns_full_content(self):
        """Test returns_full_content method."""
        assert EnumOutputMode.returns_full_content(EnumOutputMode.CONTENT)
        assert not EnumOutputMode.returns_full_content(
            EnumOutputMode.FILES_WITH_MATCHES
        )
        assert not EnumOutputMode.returns_full_content(EnumOutputMode.COUNT)

    def test_returns_file_paths(self):
        """Test returns_file_paths method."""
        assert EnumOutputMode.returns_file_paths(EnumOutputMode.FILES_WITH_MATCHES)
        assert not EnumOutputMode.returns_file_paths(EnumOutputMode.CONTENT)
        assert not EnumOutputMode.returns_file_paths(EnumOutputMode.COUNT)

    def test_returns_statistics(self):
        """Test returns_statistics method."""
        assert EnumOutputMode.returns_statistics(EnumOutputMode.COUNT)
        assert not EnumOutputMode.returns_statistics(EnumOutputMode.CONTENT)
        assert not EnumOutputMode.returns_statistics(EnumOutputMode.FILES_WITH_MATCHES)

    def test_is_minimal_output(self):
        """Test is_minimal_output method."""
        assert EnumOutputMode.is_minimal_output(EnumOutputMode.FILES_WITH_MATCHES)
        assert EnumOutputMode.is_minimal_output(EnumOutputMode.COUNT)
        assert not EnumOutputMode.is_minimal_output(EnumOutputMode.CONTENT)

    def test_is_verbose_output(self):
        """Test is_verbose_output method."""
        assert EnumOutputMode.is_verbose_output(EnumOutputMode.CONTENT)
        assert not EnumOutputMode.is_verbose_output(EnumOutputMode.FILES_WITH_MATCHES)
        assert not EnumOutputMode.is_verbose_output(EnumOutputMode.COUNT)

    def test_get_output_description(self):
        """Test get_output_description method."""
        content_desc = EnumOutputMode.get_output_description(EnumOutputMode.CONTENT)
        assert "matching lines" in content_desc.lower()
        assert "full content" in content_desc.lower()

        files_desc = EnumOutputMode.get_output_description(
            EnumOutputMode.FILES_WITH_MATCHES
        )
        assert "file paths" in files_desc.lower()

        count_desc = EnumOutputMode.get_output_description(EnumOutputMode.COUNT)
        assert "count" in count_desc.lower()

    def test_get_typical_use_case(self):
        """Test get_typical_use_case method."""
        content_case = EnumOutputMode.get_typical_use_case(EnumOutputMode.CONTENT)
        assert "content" in content_case.lower() or "analysis" in content_case.lower()

        files_case = EnumOutputMode.get_typical_use_case(
            EnumOutputMode.FILES_WITH_MATCHES
        )
        assert "files" in files_case.lower() or "patterns" in files_case.lower()

        count_case = EnumOutputMode.get_typical_use_case(EnumOutputMode.COUNT)
        assert "statistics" in count_case.lower() or "frequency" in count_case.lower()

    def test_supports_context_lines(self):
        """Test supports_context_lines method."""
        assert EnumOutputMode.supports_context_lines(EnumOutputMode.CONTENT)
        assert not EnumOutputMode.supports_context_lines(
            EnumOutputMode.FILES_WITH_MATCHES
        )
        assert not EnumOutputMode.supports_context_lines(EnumOutputMode.COUNT)

    def test_output_mode_categorization(self):
        """Test that all output modes are categorized correctly."""
        minimal_modes = {
            mode for mode in EnumOutputMode if EnumOutputMode.is_minimal_output(mode)
        }
        verbose_modes = {
            mode for mode in EnumOutputMode if EnumOutputMode.is_verbose_output(mode)
        }

        # Each mode should be either minimal or verbose
        assert minimal_modes | verbose_modes == set(EnumOutputMode)
        # No mode should be both minimal and verbose
        assert len(minimal_modes & verbose_modes) == 0

    def test_output_mode_functionality(self):
        """Test that each output mode has a specific function."""
        content_modes = {
            mode for mode in EnumOutputMode if EnumOutputMode.returns_full_content(mode)
        }
        file_modes = {
            mode for mode in EnumOutputMode if EnumOutputMode.returns_file_paths(mode)
        }
        stat_modes = {
            mode for mode in EnumOutputMode if EnumOutputMode.returns_statistics(mode)
        }

        # Each mode should have exactly one function
        all_functional_modes = content_modes | file_modes | stat_modes
        assert all_functional_modes == set(EnumOutputMode)
