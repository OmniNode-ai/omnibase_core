# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumClaudeCodeSessionStatus."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.hooks.claude_code.enum_claude_code_session_status import (
    EnumClaudeCodeSessionStatus,
)
from omnibase_core.utils.util_str_enum_base import StrValueHelper


@pytest.mark.unit
class TestEnumClaudeCodeSessionStatus:
    """Test suite for EnumClaudeCodeSessionStatus."""

    def test_enum_values_exist_and_correct(self):
        """Test that all 4 enum values exist with correct snake_case values."""
        assert EnumClaudeCodeSessionStatus.ORPHAN.value == "orphan"
        assert EnumClaudeCodeSessionStatus.ACTIVE.value == "active"
        assert EnumClaudeCodeSessionStatus.ENDED.value == "ended"
        assert EnumClaudeCodeSessionStatus.TIMED_OUT.value == "timed_out"

    def test_enum_count(self):
        """Test that enum has exactly 4 values."""
        values = list(EnumClaudeCodeSessionStatus)
        assert len(values) == 4

    def test_enum_inheritance(self):
        """Test that enum inherits from StrValueHelper, str, and Enum."""
        assert issubclass(EnumClaudeCodeSessionStatus, StrValueHelper)
        assert issubclass(EnumClaudeCodeSessionStatus, str)
        assert issubclass(EnumClaudeCodeSessionStatus, Enum)

    def test_str_value_helper_behavior(self):
        """Test that StrValueHelper provides correct __str__ behavior."""
        # str() should return the value (snake_case)
        assert str(EnumClaudeCodeSessionStatus.ORPHAN) == "orphan"
        assert str(EnumClaudeCodeSessionStatus.ACTIVE) == "active"
        assert str(EnumClaudeCodeSessionStatus.ENDED) == "ended"
        assert str(EnumClaudeCodeSessionStatus.TIMED_OUT) == "timed_out"

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings due to str inheritance."""
        status = EnumClaudeCodeSessionStatus.TIMED_OUT
        assert isinstance(status, str)
        assert status == "timed_out"
        assert len(status) == 9
        assert status.startswith("timed")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumClaudeCodeSessionStatus)
        assert EnumClaudeCodeSessionStatus.ORPHAN in values
        assert EnumClaudeCodeSessionStatus.ACTIVE in values
        assert EnumClaudeCodeSessionStatus.ENDED in values
        assert EnumClaudeCodeSessionStatus.TIMED_OUT in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "orphan" in EnumClaudeCodeSessionStatus
        assert "active" in EnumClaudeCodeSessionStatus
        assert "ended" in EnumClaudeCodeSessionStatus
        assert "timed_out" in EnumClaudeCodeSessionStatus
        assert "invalid_status" not in EnumClaudeCodeSessionStatus

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        status1 = EnumClaudeCodeSessionStatus.ACTIVE
        status2 = EnumClaudeCodeSessionStatus.ENDED

        assert status1 != status2
        assert status1 == "active"
        assert status2 == "ended"

    def test_enum_serialization(self):
        """Test that enum values can be serialized to JSON."""
        status = EnumClaudeCodeSessionStatus.TIMED_OUT
        serialized = status.value
        assert serialized == "timed_out"

        # Test JSON serialization (works due to str inheritance)
        json_str = json.dumps(status)
        assert json_str == '"timed_out"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        status = EnumClaudeCodeSessionStatus("orphan")
        assert status == EnumClaudeCodeSessionStatus.ORPHAN

        status = EnumClaudeCodeSessionStatus("timed_out")
        assert status == EnumClaudeCodeSessionStatus.TIMED_OUT

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumClaudeCodeSessionStatus("invalid_status")

        with pytest.raises(ValueError):
            EnumClaudeCodeSessionStatus("ACTIVE")  # Wrong case

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "orphan",
            "active",
            "ended",
            "timed_out",
        }

        actual_values = {member.value for member in EnumClaudeCodeSessionStatus}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumClaudeCodeSessionStatus.__doc__ is not None
        assert "Claude Code" in EnumClaudeCodeSessionStatus.__doc__

    def test_enum_uniqueness(self):
        """Test that enum values are unique (enforced by @unique decorator)."""
        values = [member.value for member in EnumClaudeCodeSessionStatus]
        assert len(values) == len(set(values))


@pytest.mark.unit
class TestIsTerminal:
    """Tests for is_terminal instance method."""

    def test_terminal_statuses_return_true(self):
        """Test that terminal statuses return True."""
        terminal_statuses = [
            EnumClaudeCodeSessionStatus.ENDED,
            EnumClaudeCodeSessionStatus.TIMED_OUT,
        ]

        for status in terminal_statuses:
            assert status.is_terminal() is True, (
                f"Expected {status} to be a terminal status"
            )

    def test_non_terminal_statuses_return_false(self):
        """Test that non-terminal statuses return False."""
        non_terminal_statuses = [
            EnumClaudeCodeSessionStatus.ORPHAN,
            EnumClaudeCodeSessionStatus.ACTIVE,
        ]

        for status in non_terminal_statuses:
            assert status.is_terminal() is False, (
                f"Expected {status} to NOT be a terminal status"
            )

    def test_terminal_status_count(self):
        """Test that exactly 2 statuses are terminal."""
        terminal_count = sum(
            1 for status in EnumClaudeCodeSessionStatus if status.is_terminal()
        )
        assert terminal_count == 2


@pytest.mark.unit
class TestIsActive:
    """Tests for is_active instance method."""

    def test_active_status_returns_true(self):
        """Test that ACTIVE status returns True."""
        assert EnumClaudeCodeSessionStatus.ACTIVE.is_active() is True

    def test_non_active_statuses_return_false(self):
        """Test that non-active statuses return False."""
        non_active_statuses = [
            EnumClaudeCodeSessionStatus.ORPHAN,
            EnumClaudeCodeSessionStatus.ENDED,
            EnumClaudeCodeSessionStatus.TIMED_OUT,
        ]

        for status in non_active_statuses:
            assert status.is_active() is False, (
                f"Expected {status} to NOT be an active status"
            )

    def test_active_status_count(self):
        """Test that exactly 1 status is active."""
        active_count = sum(
            1 for status in EnumClaudeCodeSessionStatus if status.is_active()
        )
        assert active_count == 1


@pytest.mark.unit
class TestStatusTransitions:
    """Tests for status transition logic validation."""

    def test_orphan_is_not_terminal(self):
        """Test that ORPHAN is a non-terminal state (can transition)."""
        status = EnumClaudeCodeSessionStatus.ORPHAN
        assert status.is_terminal() is False
        assert status.is_active() is False

    def test_active_is_not_terminal(self):
        """Test that ACTIVE is a non-terminal state (can transition)."""
        status = EnumClaudeCodeSessionStatus.ACTIVE
        assert status.is_terminal() is False
        assert status.is_active() is True

    def test_ended_is_terminal(self):
        """Test that ENDED is a terminal state (no further transitions)."""
        status = EnumClaudeCodeSessionStatus.ENDED
        assert status.is_terminal() is True
        assert status.is_active() is False

    def test_timed_out_is_terminal(self):
        """Test that TIMED_OUT is a terminal state (no further transitions)."""
        status = EnumClaudeCodeSessionStatus.TIMED_OUT
        assert status.is_terminal() is True
        assert status.is_active() is False

    def test_no_overlap_between_active_and_terminal(self):
        """Test that active and terminal categories are mutually exclusive."""
        for status in EnumClaudeCodeSessionStatus:
            is_active = status.is_active()
            is_terminal = status.is_terminal()

            # No status should be both active and terminal
            assert not (is_active and is_terminal), (
                f"Status {status} should not be both active and terminal"
            )

    def test_all_statuses_categorized(self):
        """Test that all statuses have defined behavior for both helper methods."""
        for status in EnumClaudeCodeSessionStatus:
            # Each status should return a boolean for both methods
            assert isinstance(status.is_active(), bool)
            assert isinstance(status.is_terminal(), bool)
