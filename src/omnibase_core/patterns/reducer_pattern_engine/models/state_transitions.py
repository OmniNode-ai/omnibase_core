"""
State Transitions - Pydantic state models for workflow lifecycle management.

Provides workflow state enumeration, state transition validation,
and state machine models with audit trails and recovery mechanisms.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, root_validator, validator

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError


class WorkflowState(str, Enum):
    """Enumeration of possible workflow states."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ModelStateTransition(BaseModel):
    """Model representing a state transition event."""

    from_state: WorkflowState
    to_state: WorkflowState
    transition_time: datetime = Field(default_factory=datetime.now)
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelWorkflowStateModel(BaseModel):
    """Complete workflow state model with transition tracking."""

    # Core identification
    workflow_id: UUID
    workflow_type: str
    instance_id: Optional[str] = None
    correlation_id: UUID

    # State management
    current_state: WorkflowState = WorkflowState.PENDING
    previous_state: Optional[WorkflowState] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Processing information
    processing_time_ms: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3

    # Error handling
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = Field(default_factory=dict)

    # Metadata and context
    metadata: Dict[str, Any] = Field(default_factory=dict)
    transition_history: List[ModelStateTransition] = Field(default_factory=list)

    # Validation
    @validator("workflow_type")
    def validate_workflow_type(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Workflow type must be a non-empty string")
        return v.lower()

    @validator("retry_count")
    def validate_retry_count(cls, v):
        if v < 0:
            raise ValueError("Retry count cannot be negative")
        return v

    @validator("max_retries")
    def validate_max_retries(cls, v):
        if v < 0:
            raise ValueError("Max retries cannot be negative")
        return v

    @root_validator
    def validate_state_consistency(cls, values):
        current_state = values.get("current_state")
        started_at = values.get("started_at")
        completed_at = values.get("completed_at")

        # If processing or completed, should have started_at
        if current_state in [
            WorkflowState.PROCESSING,
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
        ]:
            if not started_at:
                values["started_at"] = values.get("created_at") or datetime.now()

        # If completed or failed, should have completed_at
        if current_state in [
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        ]:
            if not completed_at:
                values["completed_at"] = datetime.now()

        return values

    def transition_to(
        self,
        new_state: WorkflowState,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ModelWorkflowStateModel":
        """
        Transition to a new state with validation and history tracking.

        Args:
            new_state: The target state to transition to
            reason: Optional reason for the transition
            metadata: Optional metadata for the transition

        Returns:
            Updated workflow state model

        Raises:
            ValueError: If transition is not valid
        """
        # Validate transition
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid state transition from {self.current_state} to {new_state}"
            )

        # Create transition record
        transition = ModelStateTransition(
            from_state=self.current_state,
            to_state=new_state,
            reason=reason,
            metadata=metadata or {},
        )

        # Update state
        self.previous_state = self.current_state
        self.current_state = new_state
        self.updated_at = datetime.now()

        # Update timestamps based on new state
        if new_state == WorkflowState.PROCESSING and not self.started_at:
            self.started_at = self.updated_at

        if new_state in [
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        ]:
            if not self.completed_at:
                self.completed_at = self.updated_at

            # Calculate processing time if we have start time
            if self.started_at:
                processing_duration = (
                    self.completed_at - self.started_at
                ).total_seconds() * 1000
                self.processing_time_ms = processing_duration

        # Handle retry logic
        if new_state == WorkflowState.RETRYING:
            self.retry_count += 1

        # Add to transition history
        self.transition_history.append(transition)

        return self

    def can_transition_to(self, target_state: WorkflowState) -> bool:
        """
        Check if transition to target state is valid.

        Args:
            target_state: State to transition to

        Returns:
            True if transition is valid, False otherwise
        """
        return StateTransitionValidator.is_valid_transition(
            self.current_state, target_state
        )

    def is_terminal_state(self) -> bool:
        """
        Check if current state is terminal (no further transitions possible).

        Returns:
            True if in terminal state, False otherwise
        """
        return self.current_state in [
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        ]

    def is_active_state(self) -> bool:
        """
        Check if current state is active (workflow is being processed).

        Returns:
            True if in active state, False otherwise
        """
        return self.current_state in [WorkflowState.PROCESSING, WorkflowState.RETRYING]

    def can_retry(self) -> bool:
        """
        Check if workflow can be retried.

        Returns:
            True if retry is possible, False otherwise
        """
        return (
            self.current_state == WorkflowState.FAILED
            and self.retry_count < self.max_retries
        )

    def set_error(
        self, error_message: str, error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Set error information and transition to failed state.

        Args:
            error_message: Human-readable error message
            error_details: Additional error details
        """
        self.error_message = error_message
        self.error_details = error_details or {}

        if self.current_state != WorkflowState.FAILED:
            self.transition_to(
                WorkflowState.FAILED,
                reason=f"Error: {error_message}",
                metadata={"error_details": self.error_details},
            )

    def clear_error(self) -> None:
        """Clear error information."""
        self.error_message = None
        self.error_details = {}

    def get_duration_ms(self) -> Optional[float]:
        """
        Get total workflow duration in milliseconds.

        Returns:
            Duration in milliseconds if completed, None otherwise
        """
        if self.processing_time_ms is not None:
            return self.processing_time_ms

        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000

        return None

    def get_current_duration_ms(self) -> float:
        """
        Get current workflow duration in milliseconds (even if not completed).

        Returns:
            Current duration in milliseconds
        """
        start_time = self.started_at or self.created_at
        current_time = datetime.now()
        return (current_time - start_time).total_seconds() * 1000

    def to_summary_dict(self) -> Dict[str, Any]:
        """
        Get a summary dictionary of the workflow state.

        Returns:
            Summary dictionary with key workflow information
        """
        return {
            "workflow_id": str(self.workflow_id),
            "workflow_type": self.workflow_type,
            "current_state": self.current_state.value,
            "previous_state": (
                self.previous_state.value if self.previous_state else None
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "processing_time_ms": self.processing_time_ms,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "is_terminal": self.is_terminal_state(),
            "is_active": self.is_active_state(),
            "can_retry": self.can_retry(),
            "error_message": self.error_message,
            "correlation_id": str(self.correlation_id),
            "instance_id": self.instance_id,
            "transition_count": len(self.transition_history),
        }


class StateTransitionValidator:
    """Validator for state transitions with business rules."""

    # Valid state transitions mapping
    VALID_TRANSITIONS: Dict[WorkflowState, Set[WorkflowState]] = {
        WorkflowState.PENDING: {WorkflowState.PROCESSING, WorkflowState.CANCELLED},
        WorkflowState.PROCESSING: {
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        },
        WorkflowState.COMPLETED: set(),  # Terminal state
        WorkflowState.FAILED: {WorkflowState.RETRYING, WorkflowState.CANCELLED},
        WorkflowState.CANCELLED: set(),  # Terminal state
        WorkflowState.RETRYING: {
            WorkflowState.PROCESSING,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        },
    }

    @classmethod
    def is_valid_transition(
        cls, from_state: WorkflowState, to_state: WorkflowState
    ) -> bool:
        """
        Check if a state transition is valid.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            True if transition is valid, False otherwise
        """
        return to_state in cls.VALID_TRANSITIONS.get(from_state, set())

    @classmethod
    def get_valid_transitions(cls, from_state: WorkflowState) -> Set[WorkflowState]:
        """
        Get all valid transition states from a given state.

        Args:
            from_state: Current state

        Returns:
            Set of valid target states
        """
        return cls.VALID_TRANSITIONS.get(from_state, set()).copy()

    @classmethod
    def is_terminal_state(cls, state: WorkflowState) -> bool:
        """
        Check if a state is terminal (no outgoing transitions).

        Args:
            state: State to check

        Returns:
            True if terminal state, False otherwise
        """
        return len(cls.VALID_TRANSITIONS.get(state, set())) == 0

    @classmethod
    def validate_transition_path(cls, states: List[WorkflowState]) -> bool:
        """
        Validate a sequence of state transitions.

        Args:
            states: List of states representing a transition path

        Returns:
            True if all transitions in the path are valid, False otherwise
        """
        if len(states) < 2:
            return True

        for i in range(len(states) - 1):
            if not cls.is_valid_transition(states[i], states[i + 1]):
                return False

        return True
