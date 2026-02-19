# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Integration tests for omnimemory enum system.

Tests that EnumDecisionType, EnumFailureType, and EnumSubjectType
work correctly together in memory snapshot models, validating the
architecture for the omnimemory system.
"""

import json

import pytest
from pydantic import BaseModel

from omnibase_core.enums import EnumDecisionType, EnumFailureType, EnumSubjectType


class MemorySnapshot(BaseModel):
    """Test model representing a memory snapshot.

    This model demonstrates realistic usage of the omnimemory enum system,
    combining subject identification with optional decision or failure context.
    """

    subject_type: EnumSubjectType
    subject_id: str
    decision_type: EnumDecisionType | None = None
    failure_type: EnumFailureType | None = None
    metadata: dict[str, str] | None = None


class MemoryEvent(BaseModel):
    """Test model representing a memory event with all three enums.

    Demonstrates a complete event record that might be stored in omnimemory.
    """

    event_id: str
    subject_type: EnumSubjectType
    subject_id: str
    decision_type: EnumDecisionType
    outcome_failure: EnumFailureType | None = None


@pytest.mark.unit
class TestOmnimemoryIntegration:
    """Integration tests for omnimemory enum system."""

    def test_decision_snapshot_serialization(self) -> None:
        """Test decision memory snapshot round-trip serialization."""
        snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.AGENT,
            subject_id="agent-001",
            decision_type=EnumDecisionType.MODEL_SELECTION,
        )
        # Serialize to JSON
        json_str = snapshot.model_dump_json()
        # Deserialize back
        restored = MemorySnapshot.model_validate_json(json_str)
        assert restored == snapshot
        assert restored.subject_type == EnumSubjectType.AGENT
        assert restored.decision_type == EnumDecisionType.MODEL_SELECTION
        assert restored.failure_type is None

    def test_failure_snapshot_serialization(self) -> None:
        """Test failure memory snapshot round-trip serialization."""
        snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.WORKFLOW,
            subject_id="workflow-456",
            failure_type=EnumFailureType.TIMEOUT,
        )
        # Serialize to JSON
        json_str = snapshot.model_dump_json()
        # Deserialize back
        restored = MemorySnapshot.model_validate_json(json_str)
        assert restored == snapshot
        assert restored.subject_type == EnumSubjectType.WORKFLOW
        assert restored.failure_type == EnumFailureType.TIMEOUT
        assert restored.decision_type is None

    def test_complete_event_serialization(self) -> None:
        """Test complete memory event with all enums populated."""
        event = MemoryEvent(
            event_id="evt-789",
            subject_type=EnumSubjectType.TASK,
            subject_id="task-xyz",
            decision_type=EnumDecisionType.RETRY_STRATEGY,
            outcome_failure=EnumFailureType.RATE_LIMIT,
        )
        # Full round-trip
        json_str = event.model_dump_json()
        restored = MemoryEvent.model_validate_json(json_str)
        assert restored == event
        assert restored.subject_type == EnumSubjectType.TASK
        assert restored.decision_type == EnumDecisionType.RETRY_STRATEGY
        assert restored.outcome_failure == EnumFailureType.RATE_LIMIT

    def test_json_dict_serialization(self) -> None:
        """Test serialization to dict for JSON compatibility."""
        snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.SERVICE,
            subject_id="service-api",
            decision_type=EnumDecisionType.TOOL_SELECTION,
            metadata={"context": "production"},
        )
        data = snapshot.model_dump()
        # Enum values serialize as strings
        assert data["subject_type"] == "service"
        assert data["decision_type"] == "tool_selection"
        # Can serialize to JSON string
        json_output = json.dumps(data)
        assert '"subject_type": "service"' in json_output

    def test_helper_methods_entity_vs_scope(self) -> None:
        """Test using helper methods to distinguish entity from scope subjects."""
        entity_snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.AGENT,
            subject_id="agent-001",
        )
        scope_snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.WORKFLOW,
            subject_id="workflow-123",
        )

        # Entity types
        assert entity_snapshot.subject_type.is_entity_type()
        assert not entity_snapshot.subject_type.is_scope_type()

        # Scope types
        assert scope_snapshot.subject_type.is_scope_type()
        assert not scope_snapshot.subject_type.is_entity_type()

    def test_helper_methods_retryable_failures(self) -> None:
        """Test using helper methods for retry logic decisions."""
        retryable_snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.TASK,
            subject_id="task-001",
            failure_type=EnumFailureType.TIMEOUT,
        )
        non_retryable_snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.TASK,
            subject_id="task-002",
            failure_type=EnumFailureType.INVARIANT_VIOLATION,
        )

        # Timeout is retryable
        assert retryable_snapshot.failure_type is not None
        assert retryable_snapshot.failure_type.is_retryable()

        # Invariant violations are not retryable
        assert non_retryable_snapshot.failure_type is not None
        assert not non_retryable_snapshot.failure_type.is_retryable()

    def test_helper_methods_terminal_decisions(self) -> None:
        """Test using helper methods to identify terminal decisions."""
        terminal_snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.AGENT,
            subject_id="agent-001",
            decision_type=EnumDecisionType.ESCALATION,
        )
        selection_snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.AGENT,
            subject_id="agent-001",
            decision_type=EnumDecisionType.TOOL_SELECTION,
        )

        # Escalation is terminal
        assert terminal_snapshot.decision_type is not None
        assert terminal_snapshot.decision_type.is_terminal_decision()
        assert not terminal_snapshot.decision_type.is_selection_decision()

        # Tool selection is a selection-type decision
        assert selection_snapshot.decision_type is not None
        assert selection_snapshot.decision_type.is_selection_decision()
        assert not selection_snapshot.decision_type.is_terminal_decision()

    def test_helper_methods_resource_related_failures(self) -> None:
        """Test identifying resource-related failures for alerting."""
        resource_failure = MemorySnapshot(
            subject_type=EnumSubjectType.SERVICE,
            subject_id="service-001",
            failure_type=EnumFailureType.COST_EXCEEDED,
        )
        logic_failure = MemorySnapshot(
            subject_type=EnumSubjectType.SERVICE,
            subject_id="service-001",
            failure_type=EnumFailureType.VALIDATION_ERROR,
        )

        assert resource_failure.failure_type is not None
        assert resource_failure.failure_type.is_resource_related()

        assert logic_failure.failure_type is not None
        assert not logic_failure.failure_type.is_resource_related()

    def test_helper_methods_persistence(self) -> None:
        """Test using helper methods for memory persistence decisions."""
        persistent_snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.USER,
            subject_id="user-001",
        )
        ephemeral_snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.SESSION,
            subject_id="session-abc",
        )

        # User memory is persistent
        assert persistent_snapshot.subject_type.is_persistent()
        assert persistent_snapshot.subject_type.is_entity_type()

        # Session memory is ephemeral
        assert not ephemeral_snapshot.subject_type.is_persistent()
        assert ephemeral_snapshot.subject_type.is_scope_type()

    def test_is_valid_class_methods(self) -> None:
        """Test is_valid class methods for all three enums."""
        # Valid values
        assert EnumSubjectType.is_valid("agent")
        assert EnumDecisionType.is_valid("model_selection")
        assert EnumFailureType.is_valid("timeout")

        # Invalid values
        assert not EnumSubjectType.is_valid("invalid_subject")
        assert not EnumDecisionType.is_valid("invalid_decision")
        assert not EnumFailureType.is_valid("invalid_failure")

    def test_string_coercion_in_model(self) -> None:
        """Test that string values are correctly coerced to enums in models."""
        # Pydantic should coerce strings to enums - test via explicit construction
        # (this also validates the enum constructor accepts string values)
        snapshot = MemorySnapshot(
            subject_type=EnumSubjectType("workflow"),  # string -> enum
            subject_id="wf-001",
            decision_type=EnumDecisionType("route_choice"),  # string -> enum
            failure_type=EnumFailureType("external_service"),  # string -> enum
        )
        assert snapshot.subject_type == EnumSubjectType.WORKFLOW
        assert snapshot.decision_type == EnumDecisionType.ROUTE_CHOICE
        assert snapshot.failure_type == EnumFailureType.EXTERNAL_SERVICE

    def test_realistic_workflow_scenario(self) -> None:
        """Test a realistic workflow with multiple memory snapshots."""
        # Workflow starts
        start_snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.WORKFLOW,
            subject_id="wf-processing-001",
            decision_type=EnumDecisionType.MODEL_SELECTION,
            metadata={"model": "gpt-4"},
        )

        # Task encounters transient failure
        failure_snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.TASK,
            subject_id="task-step-3",
            failure_type=EnumFailureType.RATE_LIMIT,
        )

        # Agent makes retry decision
        retry_snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.AGENT,
            subject_id="orchestrator-agent",
            decision_type=EnumDecisionType.RETRY_STRATEGY,
        )

        # Verify the workflow logic
        assert start_snapshot.subject_type.is_scope_type()
        assert start_snapshot.decision_type is not None
        assert start_snapshot.decision_type.is_selection_decision()

        assert failure_snapshot.failure_type is not None
        assert failure_snapshot.failure_type.is_retryable()
        assert failure_snapshot.failure_type.is_resource_related()

        assert retry_snapshot.subject_type.is_entity_type()
        assert retry_snapshot.decision_type is not None
        assert not retry_snapshot.decision_type.is_terminal_decision()

    def test_all_subject_types_serialization(self) -> None:
        """Test that all subject types serialize correctly."""
        for subject_type in EnumSubjectType:
            snapshot = MemorySnapshot(
                subject_type=subject_type,
                subject_id=f"test-{subject_type.value}",
            )
            json_str = snapshot.model_dump_json()
            restored = MemorySnapshot.model_validate_json(json_str)
            assert restored.subject_type == subject_type

    def test_all_decision_types_serialization(self) -> None:
        """Test that all decision types serialize correctly."""
        for decision_type in EnumDecisionType:
            snapshot = MemorySnapshot(
                subject_type=EnumSubjectType.AGENT,
                subject_id="test-agent",
                decision_type=decision_type,
            )
            json_str = snapshot.model_dump_json()
            restored = MemorySnapshot.model_validate_json(json_str)
            assert restored.decision_type == decision_type

    def test_all_failure_types_serialization(self) -> None:
        """Test that all failure types serialize correctly."""
        for failure_type in EnumFailureType:
            snapshot = MemorySnapshot(
                subject_type=EnumSubjectType.TASK,
                subject_id="test-task",
                failure_type=failure_type,
            )
            json_str = snapshot.model_dump_json()
            restored = MemorySnapshot.model_validate_json(json_str)
            assert restored.failure_type == failure_type

    def test_custom_escape_hatch_values(self) -> None:
        """Test that CUSTOM/UNKNOWN escape hatch values work correctly."""
        snapshot = MemorySnapshot(
            subject_type=EnumSubjectType.CUSTOM,
            subject_id="custom-subject",
            decision_type=EnumDecisionType.CUSTOM,
            failure_type=EnumFailureType.UNKNOWN,
        )

        # Serialize and restore
        json_str = snapshot.model_dump_json()
        restored = MemorySnapshot.model_validate_json(json_str)

        assert restored.subject_type == EnumSubjectType.CUSTOM
        assert restored.decision_type == EnumDecisionType.CUSTOM
        assert restored.failure_type == EnumFailureType.UNKNOWN

        # CUSTOM subject is neither entity nor scope (explicitly)
        assert not snapshot.subject_type.is_entity_type()
        assert not snapshot.subject_type.is_scope_type()
        # But it is persistent by default
        assert snapshot.subject_type.is_persistent()
