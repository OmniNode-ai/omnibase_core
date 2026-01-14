"""
Tests for EnumFinishReason enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_finish_reason import EnumFinishReason


@pytest.mark.unit
class TestEnumFinishReason:
    """Test cases for EnumFinishReason enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumFinishReason.STOP == "stop"
        assert EnumFinishReason.LENGTH == "length"
        assert EnumFinishReason.CONTENT_FILTER == "content_filter"
        assert EnumFinishReason.TOOL_CALLS == "tool_calls"
        assert EnumFinishReason.END_TURN == "end_turn"
        assert EnumFinishReason.MAX_TOKENS == "max_tokens"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumFinishReason, str)
        assert issubclass(EnumFinishReason, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values with StrValueHelper."""
        # StrValueHelper makes str() return the enum value
        assert str(EnumFinishReason.STOP) == "stop"
        assert str(EnumFinishReason.LENGTH) == "length"
        assert str(EnumFinishReason.CONTENT_FILTER) == "content_filter"
        assert str(EnumFinishReason.TOOL_CALLS) == "tool_calls"
        assert str(EnumFinishReason.END_TURN) == "end_turn"
        assert str(EnumFinishReason.MAX_TOKENS) == "max_tokens"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumFinishReason)
        assert len(values) == 6
        assert EnumFinishReason.STOP in values
        assert EnumFinishReason.LENGTH in values
        assert EnumFinishReason.CONTENT_FILTER in values
        assert EnumFinishReason.TOOL_CALLS in values
        assert EnumFinishReason.END_TURN in values
        assert EnumFinishReason.MAX_TOKENS in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "stop" in EnumFinishReason
        assert "length" in EnumFinishReason
        assert "content_filter" in EnumFinishReason
        assert "tool_calls" in EnumFinishReason
        assert "end_turn" in EnumFinishReason
        assert "max_tokens" in EnumFinishReason
        assert "invalid" not in EnumFinishReason

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumFinishReason.STOP == "stop"
        assert EnumFinishReason.LENGTH == "length"
        assert EnumFinishReason.CONTENT_FILTER == "content_filter"
        assert EnumFinishReason.TOOL_CALLS == "tool_calls"
        assert EnumFinishReason.END_TURN == "end_turn"
        assert EnumFinishReason.MAX_TOKENS == "max_tokens"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumFinishReason.STOP.value == "stop"
        assert EnumFinishReason.LENGTH.value == "length"
        assert EnumFinishReason.CONTENT_FILTER.value == "content_filter"
        assert EnumFinishReason.TOOL_CALLS.value == "tool_calls"
        assert EnumFinishReason.END_TURN.value == "end_turn"
        assert EnumFinishReason.MAX_TOKENS.value == "max_tokens"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumFinishReason("stop") == EnumFinishReason.STOP
        assert EnumFinishReason("length") == EnumFinishReason.LENGTH
        assert EnumFinishReason("content_filter") == EnumFinishReason.CONTENT_FILTER
        assert EnumFinishReason("tool_calls") == EnumFinishReason.TOOL_CALLS
        assert EnumFinishReason("end_turn") == EnumFinishReason.END_TURN
        assert EnumFinishReason("max_tokens") == EnumFinishReason.MAX_TOKENS

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumFinishReason("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [reason.value for reason in EnumFinishReason]
        expected_values = [
            "stop",
            "length",
            "content_filter",
            "tool_calls",
            "end_turn",
            "max_tokens",
        ]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Completion finish reasons for LLM responses" in EnumFinishReason.__doc__
