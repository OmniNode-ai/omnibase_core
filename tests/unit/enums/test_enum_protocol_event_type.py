"""Tests for EnumProtocolEventType."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_protocol_event_type import EnumProtocolEventType


@pytest.mark.unit
class TestEnumProtocolEventType:
    """Test suite for EnumProtocolEventType."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        # Lifecycle events
        assert EnumProtocolEventType.CREATED == "CREATED"
        assert EnumProtocolEventType.UPDATED == "UPDATED"
        assert EnumProtocolEventType.DELETED == "DELETED"

        # State events
        assert EnumProtocolEventType.STARTED == "STARTED"
        assert EnumProtocolEventType.COMPLETED == "COMPLETED"
        assert EnumProtocolEventType.FAILED == "FAILED"
        assert EnumProtocolEventType.CANCELLED == "CANCELLED"

        # Workflow events
        assert EnumProtocolEventType.WORKFLOW_STARTED == "WORKFLOW_STARTED"
        assert (
            EnumProtocolEventType.WORKFLOW_STEP_COMPLETED == "WORKFLOW_STEP_COMPLETED"
        )
        assert EnumProtocolEventType.WORKFLOW_COMPLETED == "WORKFLOW_COMPLETED"
        assert EnumProtocolEventType.WORKFLOW_FAILED == "WORKFLOW_FAILED"

        # Intelligence events
        assert EnumProtocolEventType.INTELLIGENCE_CAPTURED == "INTELLIGENCE_CAPTURED"
        assert EnumProtocolEventType.INTELLIGENCE_ANALYZED == "INTELLIGENCE_ANALYZED"
        assert EnumProtocolEventType.INTELLIGENCE_STORED == "INTELLIGENCE_STORED"

        # Validation events
        assert EnumProtocolEventType.VALIDATION_STARTED == "VALIDATION_STARTED"
        assert EnumProtocolEventType.VALIDATION_PASSED == "VALIDATION_PASSED"
        assert EnumProtocolEventType.VALIDATION_FAILED == "VALIDATION_FAILED"

        # Generation events
        assert EnumProtocolEventType.GENERATION_REQUESTED == "GENERATION_REQUESTED"
        assert EnumProtocolEventType.GENERATION_STARTED == "GENERATION_STARTED"
        assert EnumProtocolEventType.GENERATION_COMPLETED == "GENERATION_COMPLETED"
        assert EnumProtocolEventType.GENERATION_FAILED == "GENERATION_FAILED"

        # System events
        assert EnumProtocolEventType.HEALTH_CHECK == "HEALTH_CHECK"
        assert EnumProtocolEventType.METRICS_REPORTED == "METRICS_REPORTED"
        assert EnumProtocolEventType.ERROR_OCCURRED == "ERROR_OCCURRED"
        assert EnumProtocolEventType.WARNING_RAISED == "WARNING_RAISED"

        # Custom events
        assert EnumProtocolEventType.CUSTOM == "CUSTOM"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumProtocolEventType, str)
        assert issubclass(EnumProtocolEventType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        event = EnumProtocolEventType.CREATED
        assert isinstance(event, str)
        assert event == "CREATED"
        assert len(event) == 7

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumProtocolEventType)
        assert len(values) == 26
        assert EnumProtocolEventType.CREATED in values
        assert EnumProtocolEventType.CUSTOM in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumProtocolEventType.STARTED in EnumProtocolEventType
        assert "STARTED" in [e.value for e in EnumProtocolEventType]

    def test_enum_comparison(self):
        """Test enum comparison."""
        event1 = EnumProtocolEventType.COMPLETED
        event2 = EnumProtocolEventType.COMPLETED
        event3 = EnumProtocolEventType.FAILED

        assert event1 == event2
        assert event1 != event3
        assert event1 == "COMPLETED"

    def test_enum_serialization(self):
        """Test enum serialization."""
        event = EnumProtocolEventType.WORKFLOW_STARTED
        serialized = event.value
        assert serialized == "WORKFLOW_STARTED"
        json_str = json.dumps(event)
        assert json_str == '"WORKFLOW_STARTED"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        event = EnumProtocolEventType("VALIDATION_PASSED")
        assert event == EnumProtocolEventType.VALIDATION_PASSED

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumProtocolEventType("INVALID_EVENT")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "CREATED",
            "UPDATED",
            "DELETED",
            "STARTED",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
            "WORKFLOW_STARTED",
            "WORKFLOW_STEP_COMPLETED",
            "WORKFLOW_COMPLETED",
            "WORKFLOW_FAILED",
            "INTELLIGENCE_CAPTURED",
            "INTELLIGENCE_ANALYZED",
            "INTELLIGENCE_STORED",
            "VALIDATION_STARTED",
            "VALIDATION_PASSED",
            "VALIDATION_FAILED",
            "GENERATION_REQUESTED",
            "GENERATION_STARTED",
            "GENERATION_COMPLETED",
            "GENERATION_FAILED",
            "HEALTH_CHECK",
            "METRICS_REPORTED",
            "ERROR_OCCURRED",
            "WARNING_RAISED",
            "CUSTOM",
        }
        actual_values = {e.value for e in EnumProtocolEventType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumProtocolEventType.__doc__ is not None
        assert "event" in EnumProtocolEventType.__doc__.lower()

    def test_lifecycle_events(self):
        """Test lifecycle event grouping."""
        lifecycle_events = {
            EnumProtocolEventType.CREATED,
            EnumProtocolEventType.UPDATED,
            EnumProtocolEventType.DELETED,
        }
        assert all(event in EnumProtocolEventType for event in lifecycle_events)

    def test_state_events(self):
        """Test state event grouping."""
        state_events = {
            EnumProtocolEventType.STARTED,
            EnumProtocolEventType.COMPLETED,
            EnumProtocolEventType.FAILED,
            EnumProtocolEventType.CANCELLED,
        }
        assert all(event in EnumProtocolEventType for event in state_events)

    def test_workflow_events(self):
        """Test workflow event grouping."""
        workflow_events = {
            EnumProtocolEventType.WORKFLOW_STARTED,
            EnumProtocolEventType.WORKFLOW_STEP_COMPLETED,
            EnumProtocolEventType.WORKFLOW_COMPLETED,
            EnumProtocolEventType.WORKFLOW_FAILED,
        }
        assert all(event in EnumProtocolEventType for event in workflow_events)

    def test_intelligence_events(self):
        """Test intelligence event grouping."""
        intelligence_events = {
            EnumProtocolEventType.INTELLIGENCE_CAPTURED,
            EnumProtocolEventType.INTELLIGENCE_ANALYZED,
            EnumProtocolEventType.INTELLIGENCE_STORED,
        }
        assert all(event in EnumProtocolEventType for event in intelligence_events)

    def test_validation_events(self):
        """Test validation event grouping."""
        validation_events = {
            EnumProtocolEventType.VALIDATION_STARTED,
            EnumProtocolEventType.VALIDATION_PASSED,
            EnumProtocolEventType.VALIDATION_FAILED,
        }
        assert all(event in EnumProtocolEventType for event in validation_events)

    def test_generation_events(self):
        """Test generation event grouping."""
        generation_events = {
            EnumProtocolEventType.GENERATION_REQUESTED,
            EnumProtocolEventType.GENERATION_STARTED,
            EnumProtocolEventType.GENERATION_COMPLETED,
            EnumProtocolEventType.GENERATION_FAILED,
        }
        assert all(event in EnumProtocolEventType for event in generation_events)

    def test_system_events(self):
        """Test system event grouping."""
        system_events = {
            EnumProtocolEventType.HEALTH_CHECK,
            EnumProtocolEventType.METRICS_REPORTED,
            EnumProtocolEventType.ERROR_OCCURRED,
            EnumProtocolEventType.WARNING_RAISED,
        }
        assert all(event in EnumProtocolEventType for event in system_events)

    def test_all_events_categorized(self):
        """Test that all events are properly categorized."""
        lifecycle = {
            EnumProtocolEventType.CREATED,
            EnumProtocolEventType.UPDATED,
            EnumProtocolEventType.DELETED,
        }
        state = {
            EnumProtocolEventType.STARTED,
            EnumProtocolEventType.COMPLETED,
            EnumProtocolEventType.FAILED,
            EnumProtocolEventType.CANCELLED,
        }
        workflow = {
            EnumProtocolEventType.WORKFLOW_STARTED,
            EnumProtocolEventType.WORKFLOW_STEP_COMPLETED,
            EnumProtocolEventType.WORKFLOW_COMPLETED,
            EnumProtocolEventType.WORKFLOW_FAILED,
        }
        intelligence = {
            EnumProtocolEventType.INTELLIGENCE_CAPTURED,
            EnumProtocolEventType.INTELLIGENCE_ANALYZED,
            EnumProtocolEventType.INTELLIGENCE_STORED,
        }
        validation = {
            EnumProtocolEventType.VALIDATION_STARTED,
            EnumProtocolEventType.VALIDATION_PASSED,
            EnumProtocolEventType.VALIDATION_FAILED,
        }
        generation = {
            EnumProtocolEventType.GENERATION_REQUESTED,
            EnumProtocolEventType.GENERATION_STARTED,
            EnumProtocolEventType.GENERATION_COMPLETED,
            EnumProtocolEventType.GENERATION_FAILED,
        }
        system = {
            EnumProtocolEventType.HEALTH_CHECK,
            EnumProtocolEventType.METRICS_REPORTED,
            EnumProtocolEventType.ERROR_OCCURRED,
            EnumProtocolEventType.WARNING_RAISED,
        }
        custom = {EnumProtocolEventType.CUSTOM}

        all_categorized = (
            lifecycle
            | state
            | workflow
            | intelligence
            | validation
            | generation
            | system
            | custom
        )
        assert all_categorized == set(EnumProtocolEventType)
