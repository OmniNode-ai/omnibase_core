"""
Operation status enumeration for service operations.

Provides standardized status values for service manager operations.
"""

from enum import Enum


class EnumOperationStatus(str, Enum):
    """Enumeration for operation status values."""

    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"
    PENDING = "pending"
    TIMEOUT = "timeout"

    def is_terminal(self) -> bool:
        """Check if this status represents a terminal state."""
        return self in (
            EnumOperationStatus.SUCCESS,
            EnumOperationStatus.FAILED,
            EnumOperationStatus.CANCELLED,
            EnumOperationStatus.TIMEOUT,
        )

    def is_active(self) -> bool:
        """Check if this status represents an active operation."""
        return self in (
            EnumOperationStatus.IN_PROGRESS,
            EnumOperationStatus.PENDING,
        )

    def is_successful(self) -> bool:
        """Check if this status represents a successful operation."""
        return self == EnumOperationStatus.SUCCESS
