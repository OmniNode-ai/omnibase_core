"""
Operation status enumeration for service operations.

Provides standardized status values for operation results and API responses.
This is the canonical operation status enum (OMN-1310).

Use For:
- Operation results
- API responses
- Service manager operations
"""

from enum import Enum


class EnumOperationStatus(str, Enum):
    """
    Enumeration for operation status values.

    Canonical enum for tracking the status of operations,
    API responses, and service manager operations.
    """

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


__all__ = ["EnumOperationStatus"]
