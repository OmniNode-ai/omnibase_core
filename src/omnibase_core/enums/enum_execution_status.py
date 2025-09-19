"""
Execution status enumeration for CLI operations.

Migrated from archived and enhanced with SUCCESS value and utility methods.
Follows ONEX one-enum-per-file naming conventions.
"""

from enum import Enum


class EnumExecutionStatus(str, Enum):
    """
    Strongly typed execution status for CLI operations.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"  # From archived
    SUCCESS = "success"  # New - more specific than completed
    FAILED = "failed"
    SKIPPED = "skipped"  # From archived
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_terminal(cls, status: "EnumExecutionStatus") -> bool:
        """Check if the status represents a terminal state."""
        return status in {
            cls.COMPLETED,
            cls.SUCCESS,
            cls.FAILED,
            cls.SKIPPED,
            cls.CANCELLED,
            cls.TIMEOUT,
        }

    @classmethod
    def is_active(cls, status: "EnumExecutionStatus") -> bool:
        """Check if the status represents an active execution."""
        return status in {cls.PENDING, cls.RUNNING}

    @classmethod
    def is_successful(cls, status: "EnumExecutionStatus") -> bool:
        """Check if the status represents successful completion."""
        return status in {cls.COMPLETED, cls.SUCCESS}


# Export for use
__all__ = ["EnumExecutionStatus"]
