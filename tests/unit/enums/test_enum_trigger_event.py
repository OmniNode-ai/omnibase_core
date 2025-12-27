# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for EnumTriggerEvent enum.

Ticket: OMN-1054
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_trigger_event import EnumTriggerEvent


@pytest.mark.unit
class TestEnumTriggerEvent:
    """Test cases for EnumTriggerEvent enum."""

    def test_enum_values(self) -> None:
        """Test that enum has expected values."""
        assert EnumTriggerEvent.STAGE_COMPLETE.value == "stage_complete"
        assert EnumTriggerEvent.STEP_COMPLETE.value == "step_complete"
        assert EnumTriggerEvent.ERROR.value == "error"
        assert EnumTriggerEvent.TIMEOUT.value == "timeout"
        assert EnumTriggerEvent.MANUAL.value == "manual"
        assert EnumTriggerEvent.SCHEDULED.value == "scheduled"
        assert EnumTriggerEvent.THRESHOLD_EXCEEDED.value == "threshold_exceeded"
        assert EnumTriggerEvent.STARTUP.value == "startup"
        assert EnumTriggerEvent.SHUTDOWN.value == "shutdown"

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumTriggerEvent, str)
        assert issubclass(EnumTriggerEvent, Enum)

    def test_enum_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        trigger = EnumTriggerEvent.STAGE_COMPLETE
        assert isinstance(trigger, str)
        assert trigger.value == "stage_complete"
        assert len(trigger.value) == 14
        assert trigger.value.startswith("stage")

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated."""
        values = list(EnumTriggerEvent)
        assert len(values) == 9
        assert EnumTriggerEvent.MANUAL in values
        assert EnumTriggerEvent.SHUTDOWN in values

    def test_enum_membership(self) -> None:
        """Test enum membership operations."""
        assert "manual" in EnumTriggerEvent
        assert "invalid_trigger" not in EnumTriggerEvent

    def test_enum_comparison(self) -> None:
        """Test enum comparison operations."""
        trigger1 = EnumTriggerEvent.MANUAL
        trigger2 = EnumTriggerEvent.SCHEDULED

        assert trigger1 != trigger2
        assert trigger1.value == "manual"
        assert trigger2.value == "scheduled"
        # String comparison works due to str inheritance
        assert trigger1 == "manual"
        assert trigger2 == "scheduled"

    def test_enum_serialization(self) -> None:
        """Test that enum values can be serialized."""
        trigger = EnumTriggerEvent.ERROR
        serialized = trigger.value
        assert serialized == "error"

        # Test JSON serialization
        import json

        json_str = json.dumps(trigger)
        assert json_str == '"error"'

    def test_enum_deserialization(self) -> None:
        """Test that enum can be created from string values."""
        trigger = EnumTriggerEvent("timeout")
        assert trigger == EnumTriggerEvent.TIMEOUT

    def test_enum_invalid_value(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumTriggerEvent("invalid_trigger")

    def test_enum_all_values(self) -> None:
        """Test that all expected values are present."""
        expected_values = {
            "stage_complete",
            "step_complete",
            "error",
            "timeout",
            "manual",
            "scheduled",
            "threshold_exceeded",
            "startup",
            "shutdown",
        }

        actual_values = {member.value for member in EnumTriggerEvent}
        assert actual_values == expected_values

    def test_enum_docstring(self) -> None:
        """Test that enum has proper docstring."""
        doc = EnumTriggerEvent.__doc__
        assert doc is not None
        assert "trigger" in doc.lower()


@pytest.mark.unit
class TestEnumTriggerEventIsAutomatic:
    """Test cases for is_automatic class method."""

    def test_manual_is_not_automatic(self) -> None:
        """Test that MANUAL trigger is not automatic."""
        assert EnumTriggerEvent.is_automatic(EnumTriggerEvent.MANUAL) is False

    @pytest.mark.parametrize(
        "trigger",
        [
            EnumTriggerEvent.STAGE_COMPLETE,
            EnumTriggerEvent.STEP_COMPLETE,
            EnumTriggerEvent.ERROR,
            EnumTriggerEvent.TIMEOUT,
            EnumTriggerEvent.SCHEDULED,
            EnumTriggerEvent.THRESHOLD_EXCEEDED,
            EnumTriggerEvent.STARTUP,
            EnumTriggerEvent.SHUTDOWN,
        ],
    )
    def test_automatic_triggers_return_true(self, trigger: EnumTriggerEvent) -> None:
        """Test that automatic triggers return True."""
        assert EnumTriggerEvent.is_automatic(trigger) is True

    def test_all_triggers_are_classified(self) -> None:
        """Test that all trigger events are classified as either automatic or manual."""
        for trigger in EnumTriggerEvent:
            result = EnumTriggerEvent.is_automatic(trigger)
            assert isinstance(result, bool)

    def test_only_manual_is_not_automatic(self) -> None:
        """Test that only MANUAL trigger is not automatic."""
        non_automatic_triggers = [
            t for t in EnumTriggerEvent if not EnumTriggerEvent.is_automatic(t)
        ]
        assert len(non_automatic_triggers) == 1
        assert non_automatic_triggers[0] == EnumTriggerEvent.MANUAL


@pytest.mark.unit
class TestEnumTriggerEventIsErrorRelated:
    """Test cases for is_error_related class method."""

    @pytest.mark.parametrize(
        "trigger",
        [
            EnumTriggerEvent.ERROR,
            EnumTriggerEvent.TIMEOUT,
            EnumTriggerEvent.THRESHOLD_EXCEEDED,
        ],
    )
    def test_error_related_triggers_return_true(
        self, trigger: EnumTriggerEvent
    ) -> None:
        """Test that error-related triggers return True."""
        assert EnumTriggerEvent.is_error_related(trigger) is True

    @pytest.mark.parametrize(
        "trigger",
        [
            EnumTriggerEvent.STAGE_COMPLETE,
            EnumTriggerEvent.STEP_COMPLETE,
            EnumTriggerEvent.MANUAL,
            EnumTriggerEvent.SCHEDULED,
            EnumTriggerEvent.STARTUP,
            EnumTriggerEvent.SHUTDOWN,
        ],
    )
    def test_non_error_related_triggers_return_false(
        self, trigger: EnumTriggerEvent
    ) -> None:
        """Test that non-error-related triggers return False."""
        assert EnumTriggerEvent.is_error_related(trigger) is False

    def test_all_triggers_are_classified(self) -> None:
        """Test that all trigger events are classified for error relation."""
        for trigger in EnumTriggerEvent:
            result = EnumTriggerEvent.is_error_related(trigger)
            assert isinstance(result, bool)


@pytest.mark.unit
class TestEnumTriggerEventStrMethod:
    """Test cases for __str__ method."""

    def test_str_returns_value(self) -> None:
        """Test that __str__ returns the enum value."""
        assert str(EnumTriggerEvent.MANUAL) == "manual"
        assert str(EnumTriggerEvent.SCHEDULED) == "scheduled"
        assert str(EnumTriggerEvent.ERROR) == "error"
        assert str(EnumTriggerEvent.TIMEOUT) == "timeout"
        assert str(EnumTriggerEvent.STARTUP) == "startup"

    def test_str_in_format_string(self) -> None:
        """Test that enum works correctly in format strings."""
        trigger = EnumTriggerEvent.THRESHOLD_EXCEEDED
        formatted = f"Trigger: {trigger}"
        assert formatted == "Trigger: threshold_exceeded"


@pytest.mark.unit
class TestEnumTriggerEventEdgeCases:
    """Edge case tests for EnumTriggerEvent."""

    def test_workflow_progress_triggers(self) -> None:
        """Test that workflow progress triggers are properly categorized."""
        # Both should be automatic and not error-related
        for trigger in [
            EnumTriggerEvent.STAGE_COMPLETE,
            EnumTriggerEvent.STEP_COMPLETE,
        ]:
            assert EnumTriggerEvent.is_automatic(trigger) is True
            assert EnumTriggerEvent.is_error_related(trigger) is False

    def test_system_triggers(self) -> None:
        """Test that system triggers (startup/shutdown) are properly categorized."""
        for trigger in [EnumTriggerEvent.STARTUP, EnumTriggerEvent.SHUTDOWN]:
            assert EnumTriggerEvent.is_automatic(trigger) is True
            assert EnumTriggerEvent.is_error_related(trigger) is False

    def test_error_triggers_are_automatic(self) -> None:
        """Test that error-related triggers are also automatic (not user-initiated)."""
        error_triggers = [
            EnumTriggerEvent.ERROR,
            EnumTriggerEvent.TIMEOUT,
            EnumTriggerEvent.THRESHOLD_EXCEEDED,
        ]
        for trigger in error_triggers:
            assert EnumTriggerEvent.is_automatic(trigger) is True
            assert EnumTriggerEvent.is_error_related(trigger) is True

    def test_scheduled_is_automatic_but_not_error(self) -> None:
        """Test that scheduled triggers are automatic but not error-related."""
        assert EnumTriggerEvent.is_automatic(EnumTriggerEvent.SCHEDULED) is True
        assert EnumTriggerEvent.is_error_related(EnumTriggerEvent.SCHEDULED) is False

    def test_manual_is_neither_automatic_nor_error(self) -> None:
        """Test that manual triggers are neither automatic nor error-related."""
        assert EnumTriggerEvent.is_automatic(EnumTriggerEvent.MANUAL) is False
        assert EnumTriggerEvent.is_error_related(EnumTriggerEvent.MANUAL) is False
