"""Tests for EnumPrecommitToolNames."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_precommit_tool_names import EnumPrecommitToolNames


class TestEnumPrecommitToolNames:
    """Test suite for EnumPrecommitToolNames."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert (
            EnumPrecommitToolNames.TOOL_IDEMPOTENCY_ASSERTION_CHECKER
            == "tool_idempotency_assertion_checker"
        )

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumPrecommitToolNames, str)
        assert issubclass(EnumPrecommitToolNames, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        tool = EnumPrecommitToolNames.TOOL_IDEMPOTENCY_ASSERTION_CHECKER
        assert isinstance(tool, str)
        assert tool == "tool_idempotency_assertion_checker"
        assert len(tool) == 34

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumPrecommitToolNames)
        assert len(values) == 1
        assert EnumPrecommitToolNames.TOOL_IDEMPOTENCY_ASSERTION_CHECKER in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert (
            EnumPrecommitToolNames.TOOL_IDEMPOTENCY_ASSERTION_CHECKER
            in EnumPrecommitToolNames
        )
        assert "tool_idempotency_assertion_checker" in [
            e.value for e in EnumPrecommitToolNames
        ]

    def test_enum_comparison(self):
        """Test enum comparison."""
        tool1 = EnumPrecommitToolNames.TOOL_IDEMPOTENCY_ASSERTION_CHECKER
        tool2 = EnumPrecommitToolNames.TOOL_IDEMPOTENCY_ASSERTION_CHECKER

        assert tool1 == tool2
        assert tool1 == "tool_idempotency_assertion_checker"

    def test_enum_serialization(self):
        """Test enum serialization."""
        tool = EnumPrecommitToolNames.TOOL_IDEMPOTENCY_ASSERTION_CHECKER
        serialized = tool.value
        assert serialized == "tool_idempotency_assertion_checker"
        json_str = json.dumps(tool)
        assert json_str == '"tool_idempotency_assertion_checker"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        tool = EnumPrecommitToolNames("tool_idempotency_assertion_checker")
        assert tool == EnumPrecommitToolNames.TOOL_IDEMPOTENCY_ASSERTION_CHECKER

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumPrecommitToolNames("invalid_tool")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"tool_idempotency_assertion_checker"}
        actual_values = {e.value for e in EnumPrecommitToolNames}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumPrecommitToolNames.__doc__ is not None
        assert "pre-commit" in EnumPrecommitToolNames.__doc__.lower()

    def test_tool_naming_convention(self):
        """Test that tool names follow naming convention."""
        for tool in EnumPrecommitToolNames:
            # Should start with "tool_"
            assert tool.value.startswith("tool_")
            # Should be lowercase with underscores
            assert tool.value == tool.value.lower()
            assert " " not in tool.value

    def test_idempotency_checker_tool(self):
        """Test specific idempotency checker tool."""
        tool = EnumPrecommitToolNames.TOOL_IDEMPOTENCY_ASSERTION_CHECKER
        assert "idempotency" in tool.value
        assert "assertion" in tool.value
        assert "checker" in tool.value
