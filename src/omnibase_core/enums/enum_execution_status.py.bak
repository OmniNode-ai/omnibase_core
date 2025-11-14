"""
Execution Status Enum.

Status values for ONEX execution lifecycle tracking.
"""

from enum import Enum


class EnumExecutionStatus(str, Enum):
    """Execution status values for ONEX lifecycle tracking."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

    def __str__(self) -> str:
        """Return the string value of the execution status."""
        return self.value

    @classmethod
    def is_terminal(cls, status: "EnumExecutionStatus") -> bool:
        """
        Check if the status is terminal (execution has finished).

        Args:
            status: The status to check

        Returns:
            True if terminal, False otherwise
        """
        terminal_statuses = {
            cls.COMPLETED,
            cls.SUCCESS,
            cls.FAILED,
            cls.SKIPPED,
            cls.CANCELLED,
            cls.TIMEOUT,
        }
        return status in terminal_statuses

    @classmethod
    def is_active(cls, status: "EnumExecutionStatus") -> bool:
        """
        Check if the status is active (execution is in progress).

        Args:
            status: The status to check

        Returns:
            True if active, False otherwise
        """
        active_statuses = {cls.PENDING, cls.RUNNING}
        return status in active_statuses

    @classmethod
    def is_successful(cls, status: "EnumExecutionStatus") -> bool:
        """
        Check if the status indicates successful completion.

        Args:
            status: The status to check

        Returns:
            True if successful, False otherwise
        """
        successful_statuses = {cls.COMPLETED, cls.SUCCESS}
        return status in successful_statuses
