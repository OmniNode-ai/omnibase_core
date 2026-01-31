"""Tests for EnumClaudeCodeSessionOutcome."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.hooks.claude_code.enum_claude_code_session_outcome import (
    EnumClaudeCodeSessionOutcome,
)
from omnibase_core.utils.util_str_enum_base import StrValueHelper


@pytest.mark.unit
class TestEnumClaudeCodeSessionOutcome:
    """Test suite for EnumClaudeCodeSessionOutcome."""

    def test_enum_values_exist_and_correct(self):
        """Test that all 4 enum values exist with correct lowercase values."""
        assert EnumClaudeCodeSessionOutcome.SUCCESS.value == "success"
        assert EnumClaudeCodeSessionOutcome.FAILED.value == "failed"
        assert EnumClaudeCodeSessionOutcome.ABANDONED.value == "abandoned"
        assert EnumClaudeCodeSessionOutcome.UNKNOWN.value == "unknown"

    def test_enum_count(self):
        """Test that enum has exactly 4 values."""
        values = list(EnumClaudeCodeSessionOutcome)
        assert len(values) == 4

    def test_enum_inheritance(self):
        """Test that enum inherits from StrValueHelper, str, and Enum."""
        assert issubclass(EnumClaudeCodeSessionOutcome, StrValueHelper)
        assert issubclass(EnumClaudeCodeSessionOutcome, str)
        assert issubclass(EnumClaudeCodeSessionOutcome, Enum)

    def test_str_value_helper_behavior(self):
        """Test that StrValueHelper provides correct __str__ behavior."""
        # str() should return the value (lowercase)
        assert str(EnumClaudeCodeSessionOutcome.SUCCESS) == "success"
        assert str(EnumClaudeCodeSessionOutcome.FAILED) == "failed"
        assert str(EnumClaudeCodeSessionOutcome.ABANDONED) == "abandoned"
        assert str(EnumClaudeCodeSessionOutcome.UNKNOWN) == "unknown"

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings due to str inheritance."""
        outcome = EnumClaudeCodeSessionOutcome.ABANDONED
        assert isinstance(outcome, str)
        assert outcome == "abandoned"
        assert len(outcome) == 9
        assert outcome.startswith("abandon")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumClaudeCodeSessionOutcome)
        assert EnumClaudeCodeSessionOutcome.SUCCESS in values
        assert EnumClaudeCodeSessionOutcome.FAILED in values
        assert EnumClaudeCodeSessionOutcome.ABANDONED in values
        assert EnumClaudeCodeSessionOutcome.UNKNOWN in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "success" in EnumClaudeCodeSessionOutcome
        assert "failed" in EnumClaudeCodeSessionOutcome
        assert "abandoned" in EnumClaudeCodeSessionOutcome
        assert "unknown" in EnumClaudeCodeSessionOutcome
        assert "invalid_outcome" not in EnumClaudeCodeSessionOutcome

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        outcome1 = EnumClaudeCodeSessionOutcome.SUCCESS
        outcome2 = EnumClaudeCodeSessionOutcome.FAILED

        assert outcome1 != outcome2
        assert outcome1 == "success"
        assert outcome2 == "failed"

    def test_enum_serialization(self):
        """Test that enum values can be serialized to JSON."""
        outcome = EnumClaudeCodeSessionOutcome.ABANDONED
        serialized = outcome.value
        assert serialized == "abandoned"

        # Test JSON serialization (works due to str inheritance)
        json_str = json.dumps(outcome)
        assert json_str == '"abandoned"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        outcome = EnumClaudeCodeSessionOutcome("success")
        assert outcome == EnumClaudeCodeSessionOutcome.SUCCESS

        outcome = EnumClaudeCodeSessionOutcome("unknown")
        assert outcome == EnumClaudeCodeSessionOutcome.UNKNOWN

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumClaudeCodeSessionOutcome("invalid_outcome")

        with pytest.raises(ValueError):
            EnumClaudeCodeSessionOutcome("SUCCESS")  # Wrong case

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "success",
            "failed",
            "abandoned",
            "unknown",
        }

        actual_values = {member.value for member in EnumClaudeCodeSessionOutcome}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumClaudeCodeSessionOutcome.__doc__ is not None
        assert "Claude Code" in EnumClaudeCodeSessionOutcome.__doc__

    def test_enum_uniqueness(self):
        """Test that enum values are unique (enforced by @unique decorator)."""
        values = [member.value for member in EnumClaudeCodeSessionOutcome]
        assert len(values) == len(set(values))


@pytest.mark.unit
class TestIsTerminal:
    """Tests for is_terminal instance method."""

    def test_terminal_outcomes_return_true(self):
        """Test that terminal outcomes return True."""
        terminal_outcomes = [
            EnumClaudeCodeSessionOutcome.SUCCESS,
            EnumClaudeCodeSessionOutcome.FAILED,
            EnumClaudeCodeSessionOutcome.ABANDONED,
        ]

        for outcome in terminal_outcomes:
            assert outcome.is_terminal() is True, (
                f"Expected {outcome} to be a terminal outcome"
            )

    def test_non_terminal_outcomes_return_false(self):
        """Test that non-terminal outcomes return False."""
        non_terminal_outcomes = [
            EnumClaudeCodeSessionOutcome.UNKNOWN,
        ]

        for outcome in non_terminal_outcomes:
            assert outcome.is_terminal() is False, (
                f"Expected {outcome} to NOT be a terminal outcome"
            )

    def test_terminal_outcome_count(self):
        """Test that exactly 3 outcomes are terminal."""
        terminal_count = sum(
            1 for outcome in EnumClaudeCodeSessionOutcome if outcome.is_terminal()
        )
        assert terminal_count == 3


@pytest.mark.unit
class TestIsSuccessful:
    """Tests for is_successful instance method."""

    def test_success_outcome_returns_true(self):
        """Test that SUCCESS outcome returns True."""
        assert EnumClaudeCodeSessionOutcome.SUCCESS.is_successful() is True

    def test_non_success_outcomes_return_false(self):
        """Test that non-success outcomes return False."""
        non_success_outcomes = [
            EnumClaudeCodeSessionOutcome.FAILED,
            EnumClaudeCodeSessionOutcome.ABANDONED,
            EnumClaudeCodeSessionOutcome.UNKNOWN,
        ]

        for outcome in non_success_outcomes:
            assert outcome.is_successful() is False, (
                f"Expected {outcome} to NOT be a successful outcome"
            )

    def test_successful_outcome_count(self):
        """Test that exactly 1 outcome is successful."""
        successful_count = sum(
            1 for outcome in EnumClaudeCodeSessionOutcome if outcome.is_successful()
        )
        assert successful_count == 1


@pytest.mark.unit
class TestIsFailure:
    """Tests for is_failure instance method."""

    def test_failure_outcomes_return_true(self):
        """Test that FAILED and ABANDONED outcomes return True."""
        failure_outcomes = [
            EnumClaudeCodeSessionOutcome.FAILED,
            EnumClaudeCodeSessionOutcome.ABANDONED,
        ]

        for outcome in failure_outcomes:
            assert outcome.is_failure() is True, (
                f"Expected {outcome} to be a failure outcome"
            )

    def test_non_failure_outcomes_return_false(self):
        """Test that non-failure outcomes return False."""
        non_failure_outcomes = [
            EnumClaudeCodeSessionOutcome.SUCCESS,
            EnumClaudeCodeSessionOutcome.UNKNOWN,
        ]

        for outcome in non_failure_outcomes:
            assert outcome.is_failure() is False, (
                f"Expected {outcome} to NOT be a failure outcome"
            )

    def test_failure_outcome_count(self):
        """Test that exactly 2 outcomes are failures."""
        failure_count = sum(
            1 for outcome in EnumClaudeCodeSessionOutcome if outcome.is_failure()
        )
        assert failure_count == 2


@pytest.mark.unit
class TestOutcomeClassification:
    """Tests for outcome classification logic validation."""

    def test_success_is_terminal_and_successful(self):
        """Test that SUCCESS is terminal and successful but not a failure."""
        outcome = EnumClaudeCodeSessionOutcome.SUCCESS
        assert outcome.is_terminal() is True
        assert outcome.is_successful() is True
        assert outcome.is_failure() is False

    def test_failed_is_terminal_and_failure(self):
        """Test that FAILED is terminal and a failure but not successful."""
        outcome = EnumClaudeCodeSessionOutcome.FAILED
        assert outcome.is_terminal() is True
        assert outcome.is_successful() is False
        assert outcome.is_failure() is True

    def test_abandoned_is_terminal_and_failure(self):
        """Test that ABANDONED is terminal and a failure but not successful."""
        outcome = EnumClaudeCodeSessionOutcome.ABANDONED
        assert outcome.is_terminal() is True
        assert outcome.is_successful() is False
        assert outcome.is_failure() is True

    def test_unknown_is_non_terminal(self):
        """Test that UNKNOWN is not terminal, not successful, and not a failure."""
        outcome = EnumClaudeCodeSessionOutcome.UNKNOWN
        assert outcome.is_terminal() is False
        assert outcome.is_successful() is False
        assert outcome.is_failure() is False

    def test_no_overlap_between_success_and_failure(self):
        """Test that successful and failure categories are mutually exclusive."""
        for outcome in EnumClaudeCodeSessionOutcome:
            is_successful = outcome.is_successful()
            is_failure = outcome.is_failure()

            # No outcome should be both successful and a failure
            assert not (is_successful and is_failure), (
                f"Outcome {outcome} should not be both successful and a failure"
            )

    def test_all_outcomes_categorized(self):
        """Test that all outcomes have defined behavior for all helper methods."""
        for outcome in EnumClaudeCodeSessionOutcome:
            # Each outcome should return a boolean for all methods
            assert isinstance(outcome.is_terminal(), bool)
            assert isinstance(outcome.is_successful(), bool)
            assert isinstance(outcome.is_failure(), bool)


@pytest.mark.unit
class TestExportPaths:
    """Tests for import paths availability."""

    def test_import_from_main_enums_module(self):
        """Test that enum is importable from omnibase_core.enums."""
        from omnibase_core.enums import EnumClaudeCodeSessionOutcome as FromEnums

        assert FromEnums is EnumClaudeCodeSessionOutcome
        assert FromEnums.SUCCESS.value == "success"

    def test_import_from_hooks_module(self):
        """Test that enum is importable from omnibase_core.enums.hooks."""
        from omnibase_core.enums.hooks import (
            EnumClaudeCodeSessionOutcome as FromHooks,
        )

        assert FromHooks is EnumClaudeCodeSessionOutcome
        assert FromHooks.FAILED.value == "failed"

    def test_import_from_claude_code_module(self):
        """Test that enum is importable from omnibase_core.enums.hooks.claude_code."""
        from omnibase_core.enums.hooks.claude_code import (
            EnumClaudeCodeSessionOutcome as FromClaudeCode,
        )

        assert FromClaudeCode is EnumClaudeCodeSessionOutcome
        assert FromClaudeCode.ABANDONED.value == "abandoned"

    def test_all_import_paths_return_same_class(self):
        """Test that all import paths return the same enum class."""
        from omnibase_core.enums import EnumClaudeCodeSessionOutcome as FromEnums
        from omnibase_core.enums.hooks import (
            EnumClaudeCodeSessionOutcome as FromHooks,
        )
        from omnibase_core.enums.hooks.claude_code import (
            EnumClaudeCodeSessionOutcome as FromClaudeCode,
        )

        # All imports should be the exact same class
        assert FromEnums is FromHooks
        assert FromHooks is FromClaudeCode
        assert FromEnums is FromClaudeCode

        # Enum members should be identical
        assert FromEnums.SUCCESS is FromHooks.SUCCESS
        assert FromHooks.SUCCESS is FromClaudeCode.SUCCESS
