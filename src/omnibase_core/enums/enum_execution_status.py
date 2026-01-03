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
    PARTIAL = "partial"

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
            cls.PARTIAL,
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

    @classmethod
    def is_failure(cls, status: "EnumExecutionStatus") -> bool:
        """
        Check if the status indicates failure.

        Note that CANCELLED is neither a success nor a failure - it represents
        an intentional termination. Use :meth:`is_cancelled` to check for
        cancellation specifically.

        Args:
            status: The status to check

        Returns:
            True if failed, False otherwise
        """
        failure_statuses = {cls.FAILED, cls.TIMEOUT}
        return status in failure_statuses

    @classmethod
    def is_skipped(cls, status: "EnumExecutionStatus") -> bool:
        """
        Check if the status indicates the execution was skipped.

        Args:
            status: The status to check

        Returns:
            True if skipped, False otherwise
        """
        return status == cls.SKIPPED

    @classmethod
    def is_running(cls, status: "EnumExecutionStatus") -> bool:
        """
        Check if the status indicates the execution is currently running.

        Note: This differs from :meth:`is_active` which also includes PENDING.
        Use ``is_running`` when you specifically need to check if execution
        has started and is in progress.

        Args:
            status: The status to check

        Returns:
            True if running, False otherwise
        """
        return status == cls.RUNNING

    @classmethod
    def is_cancelled(cls, status: "EnumExecutionStatus") -> bool:
        """
        Check if the status indicates the execution was cancelled.

        CANCELLED represents an intentional termination and is neither
        a success nor a failure.

        Args:
            status: The status to check

        Returns:
            True if cancelled, False otherwise
        """
        return status == cls.CANCELLED

    @classmethod
    def is_partial(cls, status: "EnumExecutionStatus") -> bool:
        """
        Check if the status indicates partial completion.

        PARTIAL means some steps completed successfully while others failed.
        This is neither a full success nor a complete failure.

        Args:
            status: The status to check

        Returns:
            True if partial, False otherwise

        .. versionadded:: 0.4.0
            Added as part of Execution Trace infrastructure (OMN-1208)
        """
        return status == cls.PARTIAL
