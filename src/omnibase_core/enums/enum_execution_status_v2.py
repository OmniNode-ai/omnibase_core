from __future__ import annotations

"""
Execution Status Enumeration v2 - Unified Hierarchy Version.

Enhanced execution status using the unified status hierarchy. Extends base status
values with execution-specific states while eliminating conflicts with other domains.
"""


from enum import Enum, unique

from .enum_base_status import EnumBaseStatus


@unique
class EnumExecutionStatusV2(str, Enum):
    """
    Execution status enumeration extending base status hierarchy.

    Inherits fundamental status values from EnumBaseStatus and adds
    execution-specific states. Eliminates conflicts while maintaining
    all original functionality.

    Base States (from EnumBaseStatus):
    - INACTIVE, ACTIVE, PENDING (lifecycle)
    - RUNNING, COMPLETED, FAILED (execution)
    - VALID, INVALID, UNKNOWN (quality)

    Execution-Specific Extensions:
    - SUCCESS (more specific than COMPLETED)
    - SKIPPED, CANCELLED, TIMEOUT (execution outcomes)
    """

    # Base status values (inherited semantically)
    INACTIVE = EnumBaseStatus.INACTIVE.value
    ACTIVE = EnumBaseStatus.ACTIVE.value
    PENDING = EnumBaseStatus.PENDING.value
    RUNNING = EnumBaseStatus.RUNNING.value
    COMPLETED = EnumBaseStatus.COMPLETED.value
    FAILED = EnumBaseStatus.FAILED.value
    VALID = EnumBaseStatus.VALID.value
    INVALID = EnumBaseStatus.INVALID.value
    UNKNOWN = EnumBaseStatus.UNKNOWN.value

    # Execution-specific extensions
    SUCCESS = "success"  # More specific than COMPLETED
    SKIPPED = "skipped"  # Execution was skipped
    CANCELLED = "cancelled"  # Execution was cancelled
    TIMEOUT = "timeout"  # Execution timed out

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    def to_base_status(self) -> EnumBaseStatus:
        """Convert to base status enum for universal operations."""
        # Map execution-specific values to base equivalents
        base_mapping = {
            self.SUCCESS: EnumBaseStatus.COMPLETED,
            self.SKIPPED: EnumBaseStatus.INACTIVE,
            self.CANCELLED: EnumBaseStatus.INACTIVE,
            self.TIMEOUT: EnumBaseStatus.FAILED,
        }

        # If it's a direct base value, return it
        try:
            return EnumBaseStatus(self.value)
        except ValueError:
            # If it's execution-specific, map to base equivalent
            return base_mapping.get(self, EnumBaseStatus.UNKNOWN)

    @classmethod
    def from_base_status(cls, base_status: EnumBaseStatus) -> EnumExecutionStatusV2:
        """Create execution status from base status."""
        # Direct mapping for base values
        return cls(base_status.value)

    @classmethod
    def is_terminal(cls, status: EnumExecutionStatusV2) -> bool:
        """Check if the status represents a terminal state."""
        return status in {
            cls.COMPLETED,
            cls.SUCCESS,
            cls.FAILED,
            cls.SKIPPED,
            cls.CANCELLED,
            cls.TIMEOUT,
            cls.INACTIVE,
        }

    @classmethod
    def is_active(cls, status: EnumExecutionStatusV2) -> bool:
        """Check if the status represents an active execution."""
        return status in {cls.PENDING, cls.RUNNING, cls.ACTIVE}

    @classmethod
    def is_successful(cls, status: EnumExecutionStatusV2) -> bool:
        """Check if the status represents successful completion."""
        return status in {cls.COMPLETED, cls.SUCCESS}

    @classmethod
    def is_error_state(cls, status: EnumExecutionStatusV2) -> bool:
        """Check if the status represents an error state."""
        return status in {cls.FAILED, cls.TIMEOUT, cls.INVALID}

    @classmethod
    def requires_retry(cls, status: EnumExecutionStatusV2) -> bool:
        """Check if the status indicates retry might be appropriate."""
        return status in {cls.FAILED, cls.TIMEOUT, cls.CANCELLED}

    @classmethod
    def is_final_outcome(cls, status: EnumExecutionStatusV2) -> bool:
        """Check if status represents a final execution outcome."""
        return status in {cls.SUCCESS, cls.COMPLETED, cls.FAILED, cls.SKIPPED}


# Migration compatibility - provides same interface as original
# Note: Python enums cannot extend other enums, so we use module-level alias
EnumExecutionStatus = EnumExecutionStatusV2


# Export for use
__all__ = ["EnumExecutionStatus", "EnumExecutionStatusV2"]
