"""Tests for enum_learning_event_type.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_learning_event_type import EnumLearningEventType


@pytest.mark.unit
class TestEnumLearningEventType:
    """Test cases for EnumLearningEventType"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumLearningEventType.DEVELOPER_CORRECTION == "developer_correction"
        assert EnumLearningEventType.CONTEXT_SUCCESS == "context_success"
        assert EnumLearningEventType.CONTEXT_FAILURE == "context_failure"
        assert EnumLearningEventType.PATTERN_DETECTED == "pattern_detected"
        assert EnumLearningEventType.RULE_GENERATED == "rule_generated"
        assert EnumLearningEventType.RULE_VALIDATED == "rule_validated"
        assert EnumLearningEventType.RULE_PROMOTED == "rule_promoted"
        assert EnumLearningEventType.RULE_DEPRECATED == "rule_deprecated"
        assert EnumLearningEventType.WORKFLOW_STARTED == "workflow_started"
        assert EnumLearningEventType.INTELLIGENCE_EXTRACTED == "intelligence_extracted"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumLearningEventType, str)
        assert issubclass(EnumLearningEventType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumLearningEventType.DEVELOPER_CORRECTION == "developer_correction"
        assert EnumLearningEventType.CONTEXT_SUCCESS == "context_success"
        assert EnumLearningEventType.PATTERN_DETECTED == "pattern_detected"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumLearningEventType)
        assert len(values) == 10
        assert EnumLearningEventType.DEVELOPER_CORRECTION in values
        assert EnumLearningEventType.INTELLIGENCE_EXTRACTED in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumLearningEventType.DEVELOPER_CORRECTION in EnumLearningEventType
        assert "developer_correction" in EnumLearningEventType
        assert "invalid_value" not in EnumLearningEventType

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert (
            EnumLearningEventType.DEVELOPER_CORRECTION
            == EnumLearningEventType.DEVELOPER_CORRECTION
        )
        assert (
            EnumLearningEventType.CONTEXT_SUCCESS
            != EnumLearningEventType.CONTEXT_FAILURE
        )
        assert EnumLearningEventType.DEVELOPER_CORRECTION == "developer_correction"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert (
            EnumLearningEventType.DEVELOPER_CORRECTION.value == "developer_correction"
        )
        assert EnumLearningEventType.CONTEXT_SUCCESS.value == "context_success"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert (
            EnumLearningEventType("developer_correction")
            == EnumLearningEventType.DEVELOPER_CORRECTION
        )
        assert (
            EnumLearningEventType("context_success")
            == EnumLearningEventType.CONTEXT_SUCCESS
        )

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumLearningEventType("invalid_value")

        with pytest.raises(ValueError):
            EnumLearningEventType("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {
            "developer_correction",
            "context_success",
            "context_failure",
            "pattern_detected",
            "rule_generated",
            "rule_validated",
            "rule_promoted",
            "rule_deprecated",
            "workflow_started",
            "intelligence_extracted",
        }
        actual_values = {member.value for member in EnumLearningEventType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Types of learning events" in EnumLearningEventType.__doc__

    def test_enum_learning_categories(self):
        """Test specific learning event categories"""
        # Developer interaction events
        assert (
            EnumLearningEventType.DEVELOPER_CORRECTION.value == "developer_correction"
        )

        # Context events
        assert EnumLearningEventType.CONTEXT_SUCCESS.value == "context_success"
        assert EnumLearningEventType.CONTEXT_FAILURE.value == "context_failure"

        # Pattern and rule events
        assert EnumLearningEventType.PATTERN_DETECTED.value == "pattern_detected"
        assert EnumLearningEventType.RULE_GENERATED.value == "rule_generated"
        assert EnumLearningEventType.RULE_VALIDATED.value == "rule_validated"
        assert EnumLearningEventType.RULE_PROMOTED.value == "rule_promoted"
        assert EnumLearningEventType.RULE_DEPRECATED.value == "rule_deprecated"

        # Workflow events
        assert EnumLearningEventType.WORKFLOW_STARTED.value == "workflow_started"

        # Intelligence events
        assert (
            EnumLearningEventType.INTELLIGENCE_EXTRACTED.value
            == "intelligence_extracted"
        )

    def test_enum_event_flow(self):
        """Test learning event flow categories"""
        # Input events
        input_events = {
            EnumLearningEventType.DEVELOPER_CORRECTION,
            EnumLearningEventType.CONTEXT_SUCCESS,
            EnumLearningEventType.CONTEXT_FAILURE,
            EnumLearningEventType.PATTERN_DETECTED,
        }

        # Processing events
        processing_events = {
            EnumLearningEventType.RULE_GENERATED,
            EnumLearningEventType.RULE_VALIDATED,
            EnumLearningEventType.INTELLIGENCE_EXTRACTED,
        }

        # Output events
        output_events = {
            EnumLearningEventType.RULE_PROMOTED,
            EnumLearningEventType.RULE_DEPRECATED,
            EnumLearningEventType.WORKFLOW_STARTED,
        }

        all_events = set(EnumLearningEventType)
        assert input_events.union(processing_events).union(output_events) == all_events
