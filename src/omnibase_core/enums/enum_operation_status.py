"""Canonical operation status enum for ONEX framework.

**BREAKING CHANGE** (OMN-1310): This enum consolidates multiple previous
operation status enums into a single canonical source. No backwards
compatibility is provided.

**Consolidated enums**:
- EnumOperationStatus (deleted from enum_execution.py)

**Semantic Category**: Operations (API/service operation outcomes)

**Use For**:
- Operation results
- API responses
- Service manager operations

**Migration Guide**:

1. **Update imports** - Replace old imports with the canonical import::

       # Before (will cause ImportError)
       from omnibase_core.enums.enum_execution import EnumOperationStatus

       # After
       from omnibase_core.enums import EnumOperationStatus

2. **Value compatibility** - All values are preserved with identical
   string representations. No runtime value changes needed.

3. **New helper methods** - The canonical enum provides additional
   classification methods::

       status = EnumOperationStatus.SUCCESS
       status.is_terminal()    # True - execution has finished
       status.is_active()      # False - not in progress
       status.is_successful()  # True - completed successfully

**Rationale**: This consolidation eliminates duplicate EnumOperationStatus
definitions across multiple modules, providing a single authoritative source.

**Deprecation Timeline**: The old enum location was deleted in v0.6.4.
No deprecation period was provided due to internal-only usage.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import TYPE_CHECKING

from omnibase_core.utils.util_str_enum_base import StrValueHelper

if TYPE_CHECKING:
    from omnibase_core.enums.enum_base_status import EnumBaseStatus


@unique
class EnumOperationStatus(StrValueHelper, str, Enum):
    """Canonical operation status enum for API and service operations.

    This is the single source of truth for operation status values across
    the ONEX framework. Use for tracking operation outcomes, API responses,
    and service manager operations.

    **Semantic Category**: Operations (API/service outcomes)

    Values:
        SUCCESS: Operation completed successfully
        FAILED: Operation failed with an error
        IN_PROGRESS: Operation is currently executing
        CANCELLED: Operation was cancelled
        PENDING: Operation is queued but not started
        TIMEOUT: Operation exceeded time limit

    Helper Methods:
        - :meth:`is_terminal`: Check if operation has finished
        - :meth:`is_active`: Check if operation is in progress
        - :meth:`is_successful`: Check if operation succeeded
        - :meth:`to_base_status`: Convert to base status
        - :meth:`from_base_status`: Create from base status (class method)

    .. versionchanged:: 0.6.4
        Consolidated into canonical enum (OMN-1310)
    """

    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"
    PENDING = "pending"
    TIMEOUT = "timeout"

    def is_terminal(self) -> bool:
        """Check if this status represents a terminal state."""
        return self in {
            EnumOperationStatus.SUCCESS,
            EnumOperationStatus.FAILED,
            EnumOperationStatus.CANCELLED,
            EnumOperationStatus.TIMEOUT,
        }

    def is_active(self) -> bool:
        """Check if this status represents an active operation."""
        return self in {
            EnumOperationStatus.IN_PROGRESS,
            EnumOperationStatus.PENDING,
        }

    def is_successful(self) -> bool:
        """Check if this status represents a successful operation."""
        return self == EnumOperationStatus.SUCCESS

    def to_base_status(self) -> EnumBaseStatus:
        """Convert operation status to base status for universal operations.

        Maps operation-specific values to their base status equivalents:
        - SUCCESS -> COMPLETED
        - FAILED -> FAILED
        - IN_PROGRESS -> RUNNING
        - CANCELLED -> INACTIVE
        - PENDING -> PENDING
        - TIMEOUT -> FAILED

        Returns:
            The corresponding EnumBaseStatus value
        """
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        mapping = {
            self.SUCCESS: EnumBaseStatus.COMPLETED,
            self.FAILED: EnumBaseStatus.FAILED,
            self.IN_PROGRESS: EnumBaseStatus.RUNNING,
            self.CANCELLED: EnumBaseStatus.INACTIVE,
            self.PENDING: EnumBaseStatus.PENDING,
            self.TIMEOUT: EnumBaseStatus.FAILED,
        }

        return mapping.get(self, EnumBaseStatus.UNKNOWN)

    @classmethod
    def from_base_status(cls, base_status: EnumBaseStatus) -> EnumOperationStatus:
        """Create operation status from base status.

        Args:
            base_status: The base status to convert

        Returns:
            The corresponding EnumOperationStatus value

        Raises:
            ValueError: If base_status cannot be mapped to operation status
        """
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        mapping = {
            EnumBaseStatus.COMPLETED: cls.SUCCESS,
            EnumBaseStatus.FAILED: cls.FAILED,
            EnumBaseStatus.RUNNING: cls.IN_PROGRESS,
            EnumBaseStatus.INACTIVE: cls.CANCELLED,
            EnumBaseStatus.PENDING: cls.PENDING,
            EnumBaseStatus.ACTIVE: cls.IN_PROGRESS,
            EnumBaseStatus.UNKNOWN: cls.PENDING,
        }

        if base_status in mapping:
            return mapping[base_status]

        raise ValueError(  # error-ok: standard enum conversion error pattern
            f"Cannot convert {base_status} to EnumOperationStatus"
        )


__all__ = ["EnumOperationStatus"]
