"""Tests for EnumClaudeCodeHookEventType."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.hooks.claude_code.enum_claude_code_hook_event_type import (
    EnumClaudeCodeHookEventType,
)
from omnibase_core.utils.util_str_enum_base import StrValueHelper


@pytest.mark.unit
class TestEnumClaudeCodeHookEventType:
    """Test suite for EnumClaudeCodeHookEventType."""

    def test_enum_values_exist_and_correct(self):
        """Test that all 12 enum values exist with correct PascalCase values."""
        # Session lifecycle
        assert EnumClaudeCodeHookEventType.SESSION_START.value == "SessionStart"
        assert EnumClaudeCodeHookEventType.SESSION_END.value == "SessionEnd"

        # Prompt lifecycle
        assert (
            EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT.value == "UserPromptSubmit"
        )

        # Tool execution lifecycle (agentic loop)
        assert EnumClaudeCodeHookEventType.PRE_TOOL_USE.value == "PreToolUse"
        assert (
            EnumClaudeCodeHookEventType.PERMISSION_REQUEST.value == "PermissionRequest"
        )
        assert EnumClaudeCodeHookEventType.POST_TOOL_USE.value == "PostToolUse"
        assert (
            EnumClaudeCodeHookEventType.POST_TOOL_USE_FAILURE.value
            == "PostToolUseFailure"
        )

        # Subagent lifecycle
        assert EnumClaudeCodeHookEventType.SUBAGENT_START.value == "SubagentStart"
        assert EnumClaudeCodeHookEventType.SUBAGENT_STOP.value == "SubagentStop"

        # Async events
        assert EnumClaudeCodeHookEventType.NOTIFICATION.value == "Notification"

        # Session control
        assert EnumClaudeCodeHookEventType.STOP.value == "Stop"
        assert EnumClaudeCodeHookEventType.PRE_COMPACT.value == "PreCompact"

    def test_enum_count(self):
        """Test that enum has exactly 12 values."""
        values = list(EnumClaudeCodeHookEventType)
        assert len(values) == 12

    def test_enum_inheritance(self):
        """Test that enum inherits from StrValueHelper, str, and Enum."""
        assert issubclass(EnumClaudeCodeHookEventType, StrValueHelper)
        assert issubclass(EnumClaudeCodeHookEventType, str)
        assert issubclass(EnumClaudeCodeHookEventType, Enum)

    def test_str_value_helper_behavior(self):
        """Test that StrValueHelper provides correct __str__ behavior."""
        # str() should return the value (PascalCase)
        assert str(EnumClaudeCodeHookEventType.SESSION_START) == "SessionStart"
        assert str(EnumClaudeCodeHookEventType.PRE_TOOL_USE) == "PreToolUse"
        assert (
            str(EnumClaudeCodeHookEventType.POST_TOOL_USE_FAILURE)
            == "PostToolUseFailure"
        )
        assert str(EnumClaudeCodeHookEventType.NOTIFICATION) == "Notification"

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings due to str inheritance."""
        event = EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT
        assert isinstance(event, str)
        assert event == "UserPromptSubmit"
        assert len(event) == 16
        assert event.startswith("User")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumClaudeCodeHookEventType)
        assert EnumClaudeCodeHookEventType.SESSION_START in values
        assert EnumClaudeCodeHookEventType.SESSION_END in values
        assert EnumClaudeCodeHookEventType.NOTIFICATION in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "SessionStart" in EnumClaudeCodeHookEventType
        assert "PreToolUse" in EnumClaudeCodeHookEventType
        assert "InvalidEvent" not in EnumClaudeCodeHookEventType

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        event1 = EnumClaudeCodeHookEventType.PRE_TOOL_USE
        event2 = EnumClaudeCodeHookEventType.POST_TOOL_USE

        assert event1 != event2
        assert event1 == "PreToolUse"
        assert event2 == "PostToolUse"

    def test_enum_serialization(self):
        """Test that enum values can be serialized to JSON."""
        event = EnumClaudeCodeHookEventType.PERMISSION_REQUEST
        serialized = event.value
        assert serialized == "PermissionRequest"

        # Test JSON serialization (works due to str inheritance)
        json_str = json.dumps(event)
        assert json_str == '"PermissionRequest"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        event = EnumClaudeCodeHookEventType("SessionStart")
        assert event == EnumClaudeCodeHookEventType.SESSION_START

        event = EnumClaudeCodeHookEventType("PostToolUseFailure")
        assert event == EnumClaudeCodeHookEventType.POST_TOOL_USE_FAILURE

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumClaudeCodeHookEventType("InvalidEvent")

        with pytest.raises(ValueError):
            EnumClaudeCodeHookEventType("sessionstart")  # Wrong case

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "SessionStart",
            "SessionEnd",
            "UserPromptSubmit",
            "PreToolUse",
            "PermissionRequest",
            "PostToolUse",
            "PostToolUseFailure",
            "SubagentStart",
            "SubagentStop",
            "Notification",
            "Stop",
            "PreCompact",
        }

        actual_values = {member.value for member in EnumClaudeCodeHookEventType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumClaudeCodeHookEventType.__doc__ is not None
        assert "Claude Code" in EnumClaudeCodeHookEventType.__doc__


@pytest.mark.unit
class TestIsAgenticLoopEvent:
    """Tests for is_agentic_loop_event classmethod."""

    def test_agentic_loop_events_return_true(self):
        """Test that agentic loop events return True."""
        agentic_events = [
            EnumClaudeCodeHookEventType.PRE_TOOL_USE,
            EnumClaudeCodeHookEventType.PERMISSION_REQUEST,
            EnumClaudeCodeHookEventType.POST_TOOL_USE,
            EnumClaudeCodeHookEventType.POST_TOOL_USE_FAILURE,
            EnumClaudeCodeHookEventType.SUBAGENT_START,
            EnumClaudeCodeHookEventType.SUBAGENT_STOP,
        ]

        for event in agentic_events:
            assert EnumClaudeCodeHookEventType.is_agentic_loop_event(event) is True, (
                f"Expected {event} to be an agentic loop event"
            )

    def test_non_agentic_events_return_false(self):
        """Test that non-agentic events return False."""
        non_agentic_events = [
            EnumClaudeCodeHookEventType.SESSION_START,
            EnumClaudeCodeHookEventType.SESSION_END,
            EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
            EnumClaudeCodeHookEventType.NOTIFICATION,
            EnumClaudeCodeHookEventType.STOP,
            EnumClaudeCodeHookEventType.PRE_COMPACT,
        ]

        for event in non_agentic_events:
            assert EnumClaudeCodeHookEventType.is_agentic_loop_event(event) is False, (
                f"Expected {event} to NOT be an agentic loop event"
            )

    def test_agentic_loop_event_count(self):
        """Test that exactly 6 events are agentic loop events."""
        agentic_count = sum(
            1
            for event in EnumClaudeCodeHookEventType
            if EnumClaudeCodeHookEventType.is_agentic_loop_event(event)
        )
        assert agentic_count == 6


@pytest.mark.unit
class TestIsSessionLifecycleEvent:
    """Tests for is_session_lifecycle_event classmethod."""

    def test_session_lifecycle_events_return_true(self):
        """Test that session lifecycle events return True."""
        session_events = [
            EnumClaudeCodeHookEventType.SESSION_START,
            EnumClaudeCodeHookEventType.SESSION_END,
            EnumClaudeCodeHookEventType.STOP,
            EnumClaudeCodeHookEventType.PRE_COMPACT,
        ]

        for event in session_events:
            assert (
                EnumClaudeCodeHookEventType.is_session_lifecycle_event(event) is True
            ), f"Expected {event} to be a session lifecycle event"

    def test_non_session_events_return_false(self):
        """Test that non-session events return False."""
        non_session_events = [
            EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
            EnumClaudeCodeHookEventType.PRE_TOOL_USE,
            EnumClaudeCodeHookEventType.PERMISSION_REQUEST,
            EnumClaudeCodeHookEventType.POST_TOOL_USE,
            EnumClaudeCodeHookEventType.POST_TOOL_USE_FAILURE,
            EnumClaudeCodeHookEventType.SUBAGENT_START,
            EnumClaudeCodeHookEventType.SUBAGENT_STOP,
            EnumClaudeCodeHookEventType.NOTIFICATION,
        ]

        for event in non_session_events:
            assert (
                EnumClaudeCodeHookEventType.is_session_lifecycle_event(event) is False
            ), f"Expected {event} to NOT be a session lifecycle event"

    def test_session_lifecycle_event_count(self):
        """Test that exactly 4 events are session lifecycle events."""
        session_count = sum(
            1
            for event in EnumClaudeCodeHookEventType
            if EnumClaudeCodeHookEventType.is_session_lifecycle_event(event)
        )
        assert session_count == 4


@pytest.mark.unit
class TestEventCategorization:
    """Tests for event categorization completeness."""

    def test_all_events_categorized(self):
        """Test that all events fall into at least one category or are standalone."""
        # Events that are neither agentic nor session lifecycle
        standalone_events = {
            EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
            EnumClaudeCodeHookEventType.NOTIFICATION,
        }

        for event in EnumClaudeCodeHookEventType:
            is_agentic = EnumClaudeCodeHookEventType.is_agentic_loop_event(event)
            is_session = EnumClaudeCodeHookEventType.is_session_lifecycle_event(event)
            is_standalone = event in standalone_events

            # Each event should be in exactly one category
            assert is_agentic or is_session or is_standalone, (
                f"Event {event} is not categorized"
            )
            assert not (is_agentic and is_session), (
                f"Event {event} cannot be both agentic and session lifecycle"
            )

    def test_no_overlap_between_categories(self):
        """Test that agentic and session lifecycle categories don't overlap."""
        for event in EnumClaudeCodeHookEventType:
            is_agentic = EnumClaudeCodeHookEventType.is_agentic_loop_event(event)
            is_session = EnumClaudeCodeHookEventType.is_session_lifecycle_event(event)

            # No event should be in both categories
            assert not (is_agentic and is_session), (
                f"Event {event} should not be in both agentic and session categories"
            )
