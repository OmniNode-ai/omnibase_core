"""
Processing Status Enumeration

Standard processing status values for ONEX architecture.
"""

from enum import Enum


class EnumProcessingStatus(str, Enum):
    """
    Request processing status values.

    String-based enum for tracking processing lifecycle.
    """

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"

    def is_terminal(self) -> bool:
        """Check if this status represents a terminal state."""
        terminal_states = {self.COMPLETED, self.FAILED, self.TIMEOUT, self.CANCELLED}
        return self in terminal_states

    def is_active(self) -> bool:
        """Check if this status represents an active processing state."""
        active_states = {self.PENDING, self.PROCESSING}
        return self in active_states

    def can_transition_to(self, target_status: "EnumProcessingStatus") -> bool:
        """Check if transition to target status is valid."""
        valid_transitions = {
            self.PENDING: {self.PROCESSING, self.CANCELLED},
            self.PROCESSING: {
                self.COMPLETED,
                self.FAILED,
                self.TIMEOUT,
                self.CANCELLED,
            },
            # Terminal states cannot transition
            self.COMPLETED: set(),
            self.FAILED: set(),
            self.TIMEOUT: set(),
            self.CANCELLED: set(),
        }
        return target_status in valid_transitions.get(self, set())
