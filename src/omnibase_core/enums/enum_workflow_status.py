"""
Workflow Status Enumeration

Standard workflow execution status values for ONEX architecture.
"""

from enum import Enum


class EnumWorkflowStatus(str, Enum):
    """
    Workflow execution status enumeration.

    Consolidated status values for workflow lifecycle management across ONEX systems.
    """

    # Initial states
    PENDING = "pending"  # Workflow queued, waiting to start
    INITIALIZED = "initialized"  # Workflow initialized, ready to execute

    # Active states
    RUNNING = "running"  # Workflow actively executing
    PAUSED = "paused"  # Workflow temporarily suspended

    # Terminal states
    COMPLETED = "completed"  # Workflow finished successfully
    FAILED = "failed"  # Workflow failed (any reason - business logic, errors, etc.)
    CANCELLED = "cancelled"  # Workflow deliberately stopped
    SIMULATED = "simulated"  # Workflow executed in simulation mode

    def is_terminal(self) -> bool:
        """Check if this status represents a terminal state."""
        terminal_states = {self.COMPLETED, self.FAILED, self.CANCELLED, self.SIMULATED}
        return self in terminal_states

    def is_active(self) -> bool:
        """Check if this status represents an active execution state."""
        active_states = {self.RUNNING, self.PAUSED}
        return self in active_states

    def is_initial(self) -> bool:
        """Check if this status represents an initial state."""
        initial_states = {self.PENDING, self.INITIALIZED}
        return self in initial_states

    def can_transition_to(self, target_status: "EnumWorkflowStatus") -> bool:
        """Check if transition to target status is valid."""
        valid_transitions = {
            # Initial states
            self.PENDING: {self.INITIALIZED, self.RUNNING, self.CANCELLED},
            self.INITIALIZED: {self.RUNNING, self.CANCELLED},
            # Active states
            self.RUNNING: {self.PAUSED, self.COMPLETED, self.FAILED, self.CANCELLED},
            self.PAUSED: {self.RUNNING, self.CANCELLED, self.FAILED},
            # Terminal states cannot transition
            self.COMPLETED: set(),
            self.FAILED: set(),
            self.CANCELLED: set(),
            self.SIMULATED: set(),
        }
        return target_status in valid_transitions.get(self, set())
