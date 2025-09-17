"""
Fixed tests for Pydantic state machine models for workflow lifecycle management.

Tests comprehensive workflow state transitions, validation, state machine behavior,
and audit trail functionality with proper strongly typed model structure.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from omnibase_core.patterns.reducer_pattern_engine.models.state_transitions import (
    ModelStateTransition,
    ModelTransitionReason,
    ModelWorkflowIdentity,
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
        assert WorkflowState.PROCESSING.value == "processing"


class TestModelStateTransition:
    """Test ModelStateTransition model functionality."""

    def test_state_transition_creation(self):
        """Test basic ModelStateTransition model creation."""
        reason = ModelTransitionReason(
            description="Started processing",
            category="manual",
            automated=False,
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
            from_state=WorkflowState.PROCESSING,
            to_state=WorkflowState.COMPLETED,
        )

        # Reason has a default factory that creates a ModelTransitionReason
        assert transition.reason.description == "State transition"
        assert transition.reason.category == "manual"
        assert transition.reason.automated is False
        assert transition.metadata == {}
        assert isinstance(transition.transition_time, datetime)

    def test_state_transition_json_serialization(self):
        """Test ModelStateTransition JSON serialization."""
        reason = ModelTransitionReason(
            description="Test transition",
            category="automated",
            automated=True,
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
        identity = ModelWorkflowIdentity(
            workflow_id=uuid4(),
            workflow_type="DATA_ANALYSIS",
            correlation_id=uuid4(),
        )

        state_model = ModelWorkflowStateModel(identity=identity)
        assert state_model.identity.workflow_type == "data_analysis"

    def test_transition_to_valid(self):
        """Test valid state transitions."""
        identity = ModelWorkflowIdentity(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
        )

        state_model = ModelWorkflowStateModel(identity=identity)

        # PENDING -> PROCESSING
        result = state_model.transition_to(
            WorkflowState.PROCESSING,
            reason=ModelTransitionReason(
                description="Starting workflow",
                category="manual",
            ),
            metadata={"step": "initialization"},
        )

        assert result is state_model  # Returns self for chaining
        assert state_model.current_state == WorkflowState.PROCESSING
        assert state_model.previous_state == WorkflowState.PENDING
        assert state_model.timing.started_at is not None
        assert len(state_model.transition_history) == 1

        transition = state_model.transition_history[0]
        assert transition.from_state == WorkflowState.PENDING
        assert transition.to_state == WorkflowState.PROCESSING
        assert transition.reason.description == "Starting workflow"
        assert transition.metadata == {"step": "initialization"}

        # PROCESSING -> COMPLETED
        state_model.transition_to(
            WorkflowState.COMPLETED,
            reason=ModelTransitionReason(description="Work finished"),
        )

        assert state_model.current_state == WorkflowState.COMPLETED
        assert state_model.previous_state == WorkflowState.PROCESSING
        assert state_model.timing.completed_at is not None
        assert state_model.timing.processing_time_ms > 0
        assert len(state_model.transition_history) == 2

    def test_transition_to_invalid(self):
        """Test invalid state transitions raise errors."""
        identity = ModelWorkflowIdentity(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
        )

        state_model = ModelWorkflowStateModel(
            identity=identity,
            current_state=WorkflowState.COMPLETED,  # Terminal state
        )

        # Cannot transition from COMPLETED to anything
        with pytest.raises(ValueError, match="Invalid state transition"):
            state_model.transition_to(WorkflowState.PROCESSING)

    def test_transition_to_retrying(self):
        """Test transition to RETRYING state increments retry count."""
        identity = ModelWorkflowIdentity(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
        )

        state_model = ModelWorkflowStateModel(
            identity=identity,
            current_state=WorkflowState.FAILED,
        )

        initial_retry_count = state_model.retry_count
        state_model.transition_to(
            WorkflowState.RETRYING,
            reason=ModelTransitionReason(description="Retrying after failure"),
        )

        assert state_model.current_state == WorkflowState.RETRYING
        assert state_model.retry_count == initial_retry_count + 1

    def test_can_transition_to(self):
        """Test can_transition_to validation."""
        identity = ModelWorkflowIdentity(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
        )

        state_model = ModelWorkflowStateModel(identity=identity)

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
        identity = ModelWorkflowIdentity(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
        )

        state_model = ModelWorkflowStateModel(identity=identity)

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
            identity=ModelWorkflowIdentity(
                workflow_id=uuid4(),
                workflow_type="test",
                correlation_id=uuid4(),
            ),
            current_state=WorkflowState.FAILED,
        )
        assert (
            state_model.is_terminal_state() is True
        )  # FAILED is considered terminal in the implementation

        state_model = ModelWorkflowStateModel(
            identity=ModelWorkflowIdentity(
                workflow_id=uuid4(),
                workflow_type="test",
                correlation_id=uuid4(),
            ),
            current_state=WorkflowState.CANCELLED,
        )
        assert state_model.is_terminal_state() is True

    def test_is_active_state(self):
        """Test active state detection."""
        identity = ModelWorkflowIdentity(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
        )

        state_model = ModelWorkflowStateModel(identity=identity)

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
        identity = ModelWorkflowIdentity(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
        )

        state_model = ModelWorkflowStateModel(
            identity=identity,
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
        identity = ModelWorkflowIdentity(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
        )

        state_model = ModelWorkflowStateModel(
            identity=identity,
            current_state=WorkflowState.PROCESSING,
        )

        error_message = "Processing failed due to invalid input"
        error_details = {"error_code": "INVALID_INPUT", "field": "data"}

        state_model.set_error(error_message, error_details)

        assert state_model.current_state == WorkflowState.FAILED
        assert state_model.error_info.error_message == error_message
        assert state_model.error_info.error_details == error_details
        assert state_model.error_info.has_error is True

        # Should have created transition
        assert len(state_model.transition_history) == 1
        transition = state_model.transition_history[0]
        assert transition.from_state == WorkflowState.PROCESSING
        assert transition.to_state == WorkflowState.FAILED
        assert "Error:" in transition.reason.description
        assert transition.metadata["error_details"] == error_details

    def test_clear_error(self):
        """Test error clearing."""
        identity = ModelWorkflowIdentity(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
        )

        state_model = ModelWorkflowStateModel(identity=identity)

        # Set error info manually
        state_model.error_info.error_message = "Previous error"
        state_model.error_info.error_details = {"previous": "error"}
        state_model.error_info.has_error = True

        state_model.clear_error()

        assert state_model.error_info.error_message == ""
        assert state_model.error_info.error_details == {}
        assert state_model.error_info.has_error is False

    def test_get_duration_ms(self):
        """Test duration calculation."""
        identity = ModelWorkflowIdentity(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
        )

        state_model = ModelWorkflowStateModel(identity=identity)

        # For non-completed workflow, should return 0.0
        assert state_model.get_duration_ms() == 0.0

        # Set processing time manually
        state_model.timing.processing_time_ms = 1500.0
        assert state_model.get_duration_ms() == 1500.0

    def test_get_current_duration_ms(self):
        """Test current duration calculation."""
        import time

        identity = ModelWorkflowIdentity(
            workflow_id=uuid4(),
            workflow_type="test",
            correlation_id=uuid4(),
        )

        state_model = ModelWorkflowStateModel(identity=identity)

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

        identity = ModelWorkflowIdentity(
            workflow_id=workflow_id,
            workflow_type="test_workflow",
            correlation_id=correlation_id,
            instance_id="test-instance-001",
        )

        state_model = ModelWorkflowStateModel(
            identity=identity,
            retry_count=1,
            max_retries=5,
        )

        # Set error info manually
        state_model.error_info.error_message = "Test error"
        state_model.error_info.has_error = True

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
        assert (
            summary["is_terminal"] is True
        )  # FAILED is considered terminal in the implementation
        assert summary["is_active"] is False
        assert summary["can_retry"] is True
        assert summary["error_message"] == "Test error"
        assert summary["has_error"] is True
        assert summary["transition_count"] == 2

        # Check timestamps are ISO formatted
        assert isinstance(summary["created_at"], str)
        assert isinstance(summary["updated_at"], str)


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

        assert expected_valid_transitions == StateTransitionValidator.VALID_TRANSITIONS

    def test_is_valid_transition(self):
        """Test individual transition validation."""
        validator = StateTransitionValidator

        # Valid transitions
        assert (
            validator.is_valid_transition(
                WorkflowState.PENDING,
                WorkflowState.PROCESSING,
            )
            is True
        )

        assert (
            validator.is_valid_transition(
                WorkflowState.PROCESSING,
                WorkflowState.COMPLETED,
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
                WorkflowState.COMPLETED,
                WorkflowState.PROCESSING,
            )
            is False
        )

        assert (
            validator.is_valid_transition(
                WorkflowState.PENDING,
                WorkflowState.COMPLETED,
            )
            is False
        )

        assert (
            validator.is_valid_transition(
                WorkflowState.CANCELLED,
                WorkflowState.PROCESSING,
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
            WorkflowState.PROCESSING,
        )
        assert processing_transitions == {
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }

        # Terminal state transitions (empty)
        completed_transitions = validator.get_valid_transitions(WorkflowState.COMPLETED)
        assert completed_transitions == set()

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
