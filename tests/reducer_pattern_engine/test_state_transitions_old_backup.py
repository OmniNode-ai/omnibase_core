"""
Tests for Pydantic state machine models for workflow lifecycle management.

Tests comprehensive workflow state transitions, validation, state machine behavior,
and audit trail functionality for the Phase 2 implementation.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import UUID, uuid4

import pytest

from omnibase_core.patterns.reducer_pattern_engine.models.state_transitions import (
    ModelStateTransition,
    ModelWorkflowStateModel,
    StateTransitionValidator,
    WorkflowState,
)


class TestWorkflowState:
    """Test WorkflowState enum functionality."""

    def test_workflow_state_values(self):
        """Test WorkflowState enum has expected values."""
        expected_states = {
            "pending",
            "processing",
            "completed",
            "failed",
            "cancelled",
            "retrying",
        }
        actual_states = {state.value for state in WorkflowState}
        assert actual_states == expected_states

    def test_workflow_state_string_inheritance(self):
        """Test WorkflowState inherits from str."""
        assert isinstance(WorkflowState.PENDING, str)
        assert WorkflowState.PENDING == "pending"
        assert str(WorkflowState.PROCESSING) == "processing"


class TestModelStateTransition:
    """Test ModelStateTransition model functionality."""

    def test_state_transition_creation(self):
        """Test basic ModelStateTransition model creation."""
        from omnibase_core.patterns.reducer_pattern_engine.models.state_transitions import (
            ModelTransitionReason,
        )

        reason = ModelTransitionReason(
            description="Started processing", category="manual", automated=False
        )

        transition = ModelStateTransition(
            from_state=WorkflowState.PENDING,
            to_state=WorkflowState.PROCESSING,
            reason=reason,
            metadata={"priority": "high"},
        )

        assert transition.from_state == WorkflowState.PENDING
        assert transition.to_state == WorkflowState.PROCESSING
        assert transition.reason.description == "Started processing"
        assert transition.reason.category == "manual"
        assert transition.metadata == {"priority": "high"}
        assert isinstance(transition.transition_time, datetime)

    def test_state_transition_default_values(self):
        """Test ModelStateTransition with default values."""
        transition = ModelStateTransition(
            from_state=WorkflowState.PROCESSING, to_state=WorkflowState.COMPLETED
        )

        # Reason has a default factory that creates a ModelTransitionReason
        assert transition.reason.description == "State transition"
        assert transition.reason.category == "manual"
        assert transition.reason.automated is False
        assert transition.metadata == {}
        assert isinstance(transition.transition_time, datetime)

    def test_state_transition_json_serialization(self):
        """Test ModelStateTransition JSON serialization."""
        from omnibase_core.patterns.reducer_pattern_engine.models.state_transitions import (
            ModelTransitionReason,
        )

        reason = ModelTransitionReason(
            description="Test transition", category="automated", automated=True
        )

        transition = ModelStateTransition(
            from_state=WorkflowState.PENDING,
            to_state=WorkflowState.PROCESSING,
            reason=reason,
            metadata={"test": True},
        )

        # Should be able to convert to dict (using model_dump for Pydantic v2)
        transition_dict = transition.model_dump()
        assert transition_dict["from_state"] == "pending"
        assert transition_dict["to_state"] == "processing"
        assert transition_dict["reason"]["description"] == "Test transition"
        assert transition_dict["reason"]["category"] == "automated"
        assert transition_dict["metadata"] == {"test": True}

        # Should be able to recreate from dict
        recreated = ModelStateTransition(**transition_dict)
        assert recreated.from_state == transition.from_state
        assert recreated.to_state == transition.to_state


class TestModelWorkflowStateModel:
    """Test ModelWorkflowStateModel comprehensive functionality."""

    def test_workflow_state_model_creation(self):
        """Test basic ModelWorkflowStateModel creation."""
        workflow_id = uuid4()
        correlation_id = uuid4()

        from omnibase_core.patterns.reducer_pattern_engine.models.state_transitions import (
            ModelWorkflowIdentity,
        )

        identity = ModelWorkflowIdentity(
            workflow_id=workflow_id,
            workflow_type="data_analysis",
            correlation_id=correlation_id,
            instance_id="test-instance-001",
        )

        state_model = ModelWorkflowStateModel(
            identity=identity,
            metadata={"test": "value"},
        )

        assert state_model.identity.workflow_id == workflow_id
        assert state_model.identity.workflow_type == "data_analysis"
        assert state_model.identity.correlation_id == correlation_id
        assert state_model.identity.instance_id == "test-instance-001"
        assert state_model.metadata == {"test": "value"}
        assert state_model.current_state == WorkflowState.PENDING
        assert state_model.previous_state == WorkflowState.PENDING
        assert state_model.retry_count == 0
        assert state_model.max_retries == 3
        assert isinstance(state_model.timing.created_at, datetime)
        assert isinstance(state_model.timing.updated_at, datetime)
        assert state_model.transition_history == []

    def test_workflow_state_model_validation(self):
        """Test ModelWorkflowStateModel validation rules."""
        from omnibase_core.patterns.reducer_pattern_engine.models.state_transitions import (
            ModelWorkflowIdentity,
        )

        workflow_id = uuid4()
        correlation_id = uuid4()

        # Test retry_count validation
        identity = ModelWorkflowIdentity(
            workflow_id=workflow_id,
            workflow_type="test",
            correlation_id=correlation_id,
        )

        with pytest.raises(ValueError, match="Retry count cannot be negative"):
            ModelWorkflowStateModel(
                identity=identity,
                retry_count=-1,
            )

        # Test max_retries validation
        with pytest.raises(ValueError, match="Max retries cannot be negative"):
            ModelWorkflowStateModel(
                identity=identity,
                max_retries=-1,
            )

    def test_workflow_type_normalization(self):
        """Test workflow type is normalized to lowercase."""
        from omnibase_core.patterns.reducer_pattern_engine.models.state_transitions import (
            ModelWorkflowIdentity,
        )

        identity = ModelWorkflowIdentity(
            workflow_id=uuid4(), workflow_type="DATA_ANALYSIS", correlation_id=uuid4()
        )

        state_model = ModelWorkflowStateModel(identity=identity)

        assert state_model.identity.workflow_type == "data_analysis"

    def test_state_consistency_validation(self):
        """Test state consistency validation."""
        workflow_id = uuid4()
        correlation_id = uuid4()

        # Test that completed state gets timestamps
        state_model = ModelWorkflowStateModel(
            workflow_id=workflow_id,
            workflow_type="test",
            correlation_id=correlation_id,
            current_state=WorkflowState.COMPLETED,
        )

        assert state_model.started_at is not None
        assert state_model.completed_at is not None

        # Test that processing state gets started_at
        state_model = ModelWorkflowStateModel(
            workflow_id=workflow_id,
            workflow_type="test",
            correlation_id=correlation_id,
            current_state=WorkflowState.PROCESSING,
        )

        assert state_model.started_at is not None
        assert state_model.completed_at is None

    def test_transition_to_valid(self):
        """Test valid state transitions."""
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(), workflow_type="test", correlation_id=uuid4()
        )

        # PENDING -> PROCESSING
        result = state_model.transition_to(
            WorkflowState.PROCESSING,
            reason="Starting workflow",
            metadata={"step": "initialization"},
        )

        assert result is state_model  # Returns self for chaining
        assert state_model.current_state == WorkflowState.PROCESSING
        assert state_model.previous_state == WorkflowState.PENDING
        assert state_model.started_at is not None
        assert len(state_model.transition_history) == 1

        transition = state_model.transition_history[0]
        assert transition.from_state == WorkflowState.PENDING
        assert transition.to_state == WorkflowState.PROCESSING
        assert transition.reason == "Starting workflow"
        assert transition.metadata == {"step": "initialization"}

        # PROCESSING -> COMPLETED
        state_model.transition_to(WorkflowState.COMPLETED, reason="Work finished")

        assert state_model.current_state == WorkflowState.COMPLETED
        assert state_model.previous_state == WorkflowState.PROCESSING
        assert state_model.completed_at is not None
        assert state_model.processing_time_ms is not None
        assert state_model.processing_time_ms > 0
        assert len(state_model.transition_history) == 2

    def test_transition_to_invalid(self):
        """Test invalid state transitions raise errors."""
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
            current_state=WorkflowState.COMPLETED,  # Terminal state
        )

        # Cannot transition from COMPLETED to anything
        with pytest.raises(ValueError, match="Invalid state transition"):
            state_model.transition_to(WorkflowState.PROCESSING)

    def test_transition_to_retrying(self):
        """Test transition to RETRYING state increments retry count."""
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
            current_state=WorkflowState.FAILED,
        )

        initial_retry_count = state_model.retry_count
        state_model.transition_to(
            WorkflowState.RETRYING, reason="Retrying after failure"
        )

        assert state_model.current_state == WorkflowState.RETRYING
        assert state_model.retry_count == initial_retry_count + 1

    def test_can_transition_to(self):
        """Test can_transition_to validation."""
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(), workflow_type="test", correlation_id=uuid4()
        )

        # From PENDING
        assert state_model.can_transition_to(WorkflowState.PROCESSING) is True
        assert state_model.can_transition_to(WorkflowState.CANCELLED) is True
        assert state_model.can_transition_to(WorkflowState.COMPLETED) is False
        assert state_model.can_transition_to(WorkflowState.RETRYING) is False

        # Transition to PROCESSING
        state_model.transition_to(WorkflowState.PROCESSING)

        # From PROCESSING
        assert state_model.can_transition_to(WorkflowState.COMPLETED) is True
        assert state_model.can_transition_to(WorkflowState.FAILED) is True
        assert state_model.can_transition_to(WorkflowState.CANCELLED) is True
        assert state_model.can_transition_to(WorkflowState.PENDING) is False

    def test_is_terminal_state(self):
        """Test terminal state detection."""
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(), workflow_type="test", correlation_id=uuid4()
        )

        # PENDING is not terminal
        assert state_model.is_terminal_state() is False

        # PROCESSING is not terminal
        state_model.transition_to(WorkflowState.PROCESSING)
        assert state_model.is_terminal_state() is False

        # COMPLETED is terminal
        state_model.transition_to(WorkflowState.COMPLETED)
        assert state_model.is_terminal_state() is True

        # Test other terminal states
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
            current_state=WorkflowState.FAILED,
        )
        assert state_model.is_terminal_state() is False  # FAILED can retry

        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
            current_state=WorkflowState.CANCELLED,
        )
        assert state_model.is_terminal_state() is True

    def test_is_active_state(self):
        """Test active state detection."""
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(), workflow_type="test", correlation_id=uuid4()
        )

        # PENDING is not active
        assert state_model.is_active_state() is False

        # PROCESSING is active
        state_model.transition_to(WorkflowState.PROCESSING)
        assert state_model.is_active_state() is True

        # RETRYING is active
        state_model.transition_to(WorkflowState.FAILED)
        state_model.transition_to(WorkflowState.RETRYING)
        assert state_model.is_active_state() is True

        # COMPLETED is not active
        state_model.transition_to(WorkflowState.PROCESSING)
        state_model.transition_to(WorkflowState.COMPLETED)
        assert state_model.is_active_state() is False

    def test_can_retry(self):
        """Test retry capability detection."""
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
            max_retries=2,
        )

        # PENDING cannot retry
        assert state_model.can_retry() is False

        # FAILED can retry if under max_retries
        state_model.transition_to(WorkflowState.PROCESSING)
        state_model.transition_to(WorkflowState.FAILED)
        assert state_model.can_retry() is True

        # After first retry
        state_model.transition_to(WorkflowState.RETRYING)
        state_model.transition_to(WorkflowState.FAILED)
        assert state_model.can_retry() is True  # retry_count = 1, max = 2

        # After second retry (at max)
        state_model.transition_to(WorkflowState.RETRYING)
        state_model.transition_to(WorkflowState.FAILED)
        assert state_model.can_retry() is False  # retry_count = 2, max = 2

    def test_set_error(self):
        """Test error setting and state transition."""
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
            current_state=WorkflowState.PROCESSING,
        )

        error_message = "Processing failed due to invalid input"
        error_details = {"error_code": "INVALID_INPUT", "field": "data"}

        state_model.set_error(error_message, error_details)

        assert state_model.current_state == WorkflowState.FAILED
        assert state_model.error_message == error_message
        assert state_model.error_details == error_details

        # Should have created transition
        assert len(state_model.transition_history) == 1
        transition = state_model.transition_history[0]
        assert transition.from_state == WorkflowState.PROCESSING
        assert transition.to_state == WorkflowState.FAILED
        assert "Error:" in transition.reason
        assert transition.metadata["error_details"] == error_details

    def test_clear_error(self):
        """Test error clearing."""
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
            error_message="Previous error",
            error_details={"previous": "error"},
        )

        state_model.clear_error()

        assert state_model.error_message is None
        assert state_model.error_details == {}

    def test_get_duration_ms(self):
        """Test duration calculation."""
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(), workflow_type="test", correlation_id=uuid4()
        )

        # No duration for non-completed workflow
        assert state_model.get_duration_ms() is None

        # Set processing time manually
        state_model.processing_time_ms = 1500.0
        assert state_model.get_duration_ms() == 1500.0

        # Test with actual timestamps
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=2.5)

        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
            started_at=start_time,
            completed_at=end_time,
        )

        duration = state_model.get_duration_ms()
        assert duration is not None
        assert 2400 <= duration <= 2600  # ~2500ms with tolerance

    def test_get_current_duration_ms(self):
        """Test current duration calculation."""
        import time

        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(), workflow_type="test", correlation_id=uuid4()
        )

        # Should return positive duration
        duration1 = state_model.get_current_duration_ms()
        assert duration1 >= 0

        # Wait a bit and check duration increased
        time.sleep(0.1)
        duration2 = state_model.get_current_duration_ms()
        assert duration2 > duration1

    def test_to_summary_dict(self):
        """Test summary dictionary creation."""
        workflow_id = uuid4()
        correlation_id = uuid4()

        state_model = ModelWorkflowStateModel(
            workflow_id=workflow_id,
            workflow_type="test_workflow",
            correlation_id=correlation_id,
            instance_id="test-instance-001",
            retry_count=1,
            max_retries=5,
            error_message="Test error",
        )

        # Add some transitions
        state_model.transition_to(WorkflowState.PROCESSING)
        state_model.transition_to(WorkflowState.FAILED)

        summary = state_model.to_summary_dict()

        # Verify summary structure and content
        assert summary["workflow_id"] == str(workflow_id)
        assert summary["workflow_type"] == "test_workflow"
        assert summary["current_state"] == "failed"
        assert summary["previous_state"] == "processing"
        assert summary["correlation_id"] == str(correlation_id)
        assert summary["instance_id"] == "test-instance-001"
        assert summary["retry_count"] == 1
        assert summary["max_retries"] == 5
        assert summary["is_terminal"] is False  # FAILED can retry
        assert summary["is_active"] is False
        assert summary["can_retry"] is True
        assert summary["error_message"] == "Test error"
        assert summary["transition_count"] == 2

        # Check timestamps are ISO formatted
        assert isinstance(summary["created_at"], str)
        assert isinstance(summary["updated_at"], str)
        assert summary["completed_at"] is None  # Not completed


class TestStateTransitionValidator:
    """Test StateTransitionValidator functionality."""

    def test_valid_transitions_mapping(self):
        """Test that valid transitions mapping is correct."""
        expected_valid_transitions = {
            WorkflowState.PENDING: {WorkflowState.PROCESSING, WorkflowState.CANCELLED},
            WorkflowState.PROCESSING: {
                WorkflowState.COMPLETED,
                WorkflowState.FAILED,
                WorkflowState.CANCELLED,
            },
            WorkflowState.COMPLETED: set(),  # Terminal
            WorkflowState.FAILED: {WorkflowState.RETRYING, WorkflowState.CANCELLED},
            WorkflowState.CANCELLED: set(),  # Terminal
            WorkflowState.RETRYING: {
                WorkflowState.PROCESSING,
                WorkflowState.FAILED,
                WorkflowState.CANCELLED,
            },
        }

        assert StateTransitionValidator.VALID_TRANSITIONS == expected_valid_transitions

    def test_is_valid_transition(self):
        """Test individual transition validation."""
        validator = StateTransitionValidator

        # Valid transitions
        assert (
            validator.is_valid_transition(
                WorkflowState.PENDING, WorkflowState.PROCESSING
            )
            is True
        )

        assert (
            validator.is_valid_transition(
                WorkflowState.PROCESSING, WorkflowState.COMPLETED
            )
            is True
        )

        assert (
            validator.is_valid_transition(WorkflowState.FAILED, WorkflowState.RETRYING)
            is True
        )

        # Invalid transitions
        assert (
            validator.is_valid_transition(
                WorkflowState.COMPLETED, WorkflowState.PROCESSING
            )
            is False
        )

        assert (
            validator.is_valid_transition(
                WorkflowState.PENDING, WorkflowState.COMPLETED
            )
            is False
        )

        assert (
            validator.is_valid_transition(
                WorkflowState.CANCELLED, WorkflowState.PROCESSING
            )
            is False
        )

    def test_get_valid_transitions(self):
        """Test getting valid transitions from a state."""
        validator = StateTransitionValidator

        # PENDING state transitions
        pending_transitions = validator.get_valid_transitions(WorkflowState.PENDING)
        assert pending_transitions == {
            WorkflowState.PROCESSING,
            WorkflowState.CANCELLED,
        }

        # PROCESSING state transitions
        processing_transitions = validator.get_valid_transitions(
            WorkflowState.PROCESSING
        )
        assert processing_transitions == {
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }

        # Terminal state transitions (empty)
        completed_transitions = validator.get_valid_transitions(WorkflowState.COMPLETED)
        assert completed_transitions == set()

        # Non-existent state (should return empty set)
        class FakeState:
            pass

        fake_transitions = validator.get_valid_transitions(FakeState())
        assert fake_transitions == set()

    def test_is_terminal_state(self):
        """Test terminal state detection."""
        validator = StateTransitionValidator

        # Terminal states
        assert validator.is_terminal_state(WorkflowState.COMPLETED) is True
        assert validator.is_terminal_state(WorkflowState.CANCELLED) is True

        # Non-terminal states
        assert validator.is_terminal_state(WorkflowState.PENDING) is False
        assert validator.is_terminal_state(WorkflowState.PROCESSING) is False
        assert validator.is_terminal_state(WorkflowState.FAILED) is False
        assert validator.is_terminal_state(WorkflowState.RETRYING) is False

    def test_validate_transition_path(self):
        """Test validation of transition sequences."""
        validator = StateTransitionValidator

        # Valid paths
        valid_path_1 = [
            WorkflowState.PENDING,
            WorkflowState.PROCESSING,
            WorkflowState.COMPLETED,
        ]
        assert validator.validate_transition_path(valid_path_1) is True

        valid_path_2 = [
            WorkflowState.PENDING,
            WorkflowState.PROCESSING,
            WorkflowState.FAILED,
            WorkflowState.RETRYING,
            WorkflowState.PROCESSING,
            WorkflowState.COMPLETED,
        ]
        assert validator.validate_transition_path(valid_path_2) is True

        # Single state (always valid)
        assert validator.validate_transition_path([WorkflowState.PENDING]) is True

        # Empty path (always valid)
        assert validator.validate_transition_path([]) is True

        # Invalid paths
        invalid_path_1 = [
            WorkflowState.PENDING,
            WorkflowState.COMPLETED,  # Cannot go directly from PENDING to COMPLETED
        ]
        assert validator.validate_transition_path(invalid_path_1) is False

        invalid_path_2 = [
            WorkflowState.COMPLETED,
            WorkflowState.PROCESSING,  # Cannot transition from terminal state
        ]
        assert validator.validate_transition_path(invalid_path_2) is False

        invalid_path_3 = [
            WorkflowState.PENDING,
            WorkflowState.PROCESSING,
            WorkflowState.COMPLETED,
            WorkflowState.RETRYING,  # Cannot transition from COMPLETED
        ]
        assert validator.validate_transition_path(invalid_path_3) is False

    def test_complex_workflow_scenarios(self):
        """Test complex workflow scenarios using the state machine."""
        # Scenario 1: Successful workflow
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(),
            workflow_type="successful_workflow",
            correlation_id=uuid4(),
        )

        # PENDING -> PROCESSING -> COMPLETED
        state_model.transition_to(WorkflowState.PROCESSING, reason="Starting work")
        state_model.transition_to(
            WorkflowState.COMPLETED, reason="Work finished successfully"
        )

        assert state_model.current_state == WorkflowState.COMPLETED
        assert state_model.is_terminal_state() is True
        assert len(state_model.transition_history) == 2

        # Scenario 2: Failed workflow with retry
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(),
            workflow_type="retry_workflow",
            correlation_id=uuid4(),
            max_retries=2,
        )

        # PENDING -> PROCESSING -> FAILED -> RETRYING -> PROCESSING -> COMPLETED
        state_model.transition_to(WorkflowState.PROCESSING, reason="Starting work")
        state_model.transition_to(WorkflowState.FAILED, reason="First attempt failed")
        assert state_model.can_retry() is True

        state_model.transition_to(
            WorkflowState.RETRYING, reason="Retrying after failure"
        )
        assert state_model.retry_count == 1

        state_model.transition_to(WorkflowState.PROCESSING, reason="Retry attempt")
        state_model.transition_to(WorkflowState.COMPLETED, reason="Retry succeeded")

        assert state_model.current_state == WorkflowState.COMPLETED
        assert state_model.retry_count == 1
        assert len(state_model.transition_history) == 5

        # Scenario 3: Cancelled workflow
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(),
            workflow_type="cancelled_workflow",
            correlation_id=uuid4(),
        )

        # PENDING -> PROCESSING -> CANCELLED
        state_model.transition_to(WorkflowState.PROCESSING, reason="Starting work")
        state_model.transition_to(WorkflowState.CANCELLED, reason="User cancelled")

        assert state_model.current_state == WorkflowState.CANCELLED
        assert state_model.is_terminal_state() is True
        assert not state_model.can_retry()

        # Scenario 4: Maximum retries exceeded
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(),
            workflow_type="max_retry_workflow",
            correlation_id=uuid4(),
            max_retries=1,
        )

        # Use up all retries
        state_model.transition_to(WorkflowState.PROCESSING)
        state_model.transition_to(WorkflowState.FAILED)
        state_model.transition_to(WorkflowState.RETRYING)  # retry_count = 1
        state_model.transition_to(WorkflowState.FAILED)

        # Should not be able to retry anymore
        assert state_model.can_retry() is False
        assert state_model.retry_count == 1
        assert state_model.max_retries == 1

    def test_transition_metadata_preservation(self):
        """Test that transition metadata is properly preserved."""
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(), workflow_type="metadata_test", correlation_id=uuid4()
        )

        # Transition with rich metadata
        metadata_1 = {
            "user_id": "test-user-123",
            "priority": "high",
            "estimated_duration": 300,
            "context": {"source": "api", "version": "2.1"},
        }

        state_model.transition_to(
            WorkflowState.PROCESSING,
            reason="Started by API request",
            metadata=metadata_1,
        )

        # Transition with different metadata
        metadata_2 = {
            "completion_percentage": 100,
            "result_size": 1024,
            "performance_metrics": {"cpu_usage": 15.5, "memory_mb": 256},
        }

        state_model.transition_to(
            WorkflowState.COMPLETED,
            reason="Processing completed successfully",
            metadata=metadata_2,
        )

        # Verify transition history preserves metadata
        assert len(state_model.transition_history) == 2

        first_transition = state_model.transition_history[0]
        assert first_transition.metadata == metadata_1
        assert first_transition.reason == "Started by API request"

        second_transition = state_model.transition_history[1]
        assert second_transition.metadata == metadata_2
        assert second_transition.reason == "Processing completed successfully"

        # Verify metadata isolation (modifying original shouldn't affect stored)
        metadata_1["priority"] = "modified"
        assert state_model.transition_history[0].metadata["priority"] == "high"

    def test_state_model_immutability_after_terminal(self):
        """Test that state model behavior after reaching terminal states."""
        state_model = ModelWorkflowStateModel(
            workflow_id=uuid4(), workflow_type="terminal_test", correlation_id=uuid4()
        )

        # Complete the workflow
        state_model.transition_to(WorkflowState.PROCESSING)
        state_model.transition_to(WorkflowState.COMPLETED)

        # Should not be able to transition further
        with pytest.raises(ValueError, match="Invalid state transition"):
            state_model.transition_to(WorkflowState.PROCESSING)

        with pytest.raises(ValueError, match="Invalid state transition"):
            state_model.transition_to(WorkflowState.RETRYING)

        # Error setting should also fail silently or handle gracefully
        original_state = state_model.current_state
        state_model.set_error("Post-completion error", {"test": True})

        # State should remain the same (COMPLETED)
        assert state_model.current_state == original_state

        # But error information might still be set for audit purposes
        # (This depends on implementation choice - could be either way)
