"""Canonical execution status enum for ONEX framework.

**BREAKING CHANGE** (OMN-1310): This enum consolidates multiple previous
execution status enums into a single canonical source. No backwards
compatibility is provided.

**Consolidated enums**:
- EnumExecutionStatusV2 (deleted from enum_execution_status_v2.py)

**Migration Guide**:

1. **Update imports** - Replace old imports with the canonical import::

       # Before (will cause ImportError)
       from omnibase_core.enums.enum_execution_status_v2 import EnumExecutionStatusV2

       # After
       from omnibase_core.enums import EnumExecutionStatus

2. **Update type annotations** - Replace type references::

       # Before
       def process(status: EnumExecutionStatusV2) -> None: ...

       # After
       def process(status: EnumExecutionStatus) -> None: ...

3. **Value compatibility** - All values from the deleted enum exist in this
   enum with identical string representations. No runtime value changes needed.

**Rationale**: This consolidation eliminates enum proliferation and provides
a single source of truth for execution status values. The unified enum
includes helper methods (is_terminal, is_active, etc.) for consistent
status classification across the codebase.

**Deprecation Timeline**: The old enum files were deleted in v0.6.4.
No deprecation period was provided due to internal-only usage.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import TYPE_CHECKING

from omnibase_core.utils.util_str_enum_base import StrValueHelper

if TYPE_CHECKING:
    from omnibase_core.enums.enum_base_status import EnumBaseStatus


@unique
class EnumExecutionStatus(StrValueHelper, str, Enum):
    """Canonical execution status enum for ONEX lifecycle tracking.

    This is the single source of truth for execution status values across
    the ONEX framework. All execution-related status tracking should use
    this enum.

    **Semantic Category**: Execution (task/job/step completion states)

    Values:
        PENDING: Execution is queued but not yet started
        RUNNING: Execution is in progress
        COMPLETED: Execution finished (generic completion)
        SUCCESS: Execution completed successfully
        FAILED: Execution failed with an error
        SKIPPED: Execution was skipped
        CANCELLED: Execution was cancelled by user or system
        TIMEOUT: Execution exceeded time limit
        PARTIAL: Execution partially completed (some steps succeeded).
            Example: In a batch job of 100 items, 75 succeeded and 25 failed -
            neither full SUCCESS nor complete FAILURE.

    Helper Methods:
        - :meth:`is_terminal`: Check if execution has finished
        - :meth:`is_active`: Check if execution is in progress
        - :meth:`is_successful`: Check if execution succeeded
        - :meth:`is_failure`: Check if execution failed
        - :meth:`to_base_status`: Convert to EnumBaseStatus
        - :meth:`from_base_status`: Create from EnumBaseStatus

    .. versionchanged:: 0.6.4
        Consolidated EnumExecutionStatusV2 into this enum (OMN-1310)
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    PARTIAL = "partial"

    def to_base_status(self) -> EnumBaseStatus:
        """
        Convert execution status to base status for universal operations.

        Maps execution-specific values to their base status equivalents:
        - SUCCESS -> COMPLETED
        - SKIPPED -> INACTIVE
        - CANCELLED -> INACTIVE
        - TIMEOUT -> FAILED
        - PARTIAL -> COMPLETED (with partial success)

        Returns:
            The corresponding EnumBaseStatus value
        """
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        # Direct mappings for values that exist in base
        direct_mappings = {
            self.PENDING: EnumBaseStatus.PENDING,
            self.RUNNING: EnumBaseStatus.RUNNING,
            self.COMPLETED: EnumBaseStatus.COMPLETED,
            self.FAILED: EnumBaseStatus.FAILED,
        }

        if self in direct_mappings:
            return direct_mappings[self]

        # Execution-specific mappings
        execution_mappings = {
            self.SUCCESS: EnumBaseStatus.COMPLETED,
            self.SKIPPED: EnumBaseStatus.INACTIVE,
            self.CANCELLED: EnumBaseStatus.INACTIVE,
            self.TIMEOUT: EnumBaseStatus.FAILED,
            self.PARTIAL: EnumBaseStatus.COMPLETED,
        }

        return execution_mappings.get(self, EnumBaseStatus.UNKNOWN)

    @classmethod
    def from_base_status(cls, base_status: EnumBaseStatus) -> EnumExecutionStatus:
        """
        Create execution status from base status.

        Args:
            base_status: The base status to convert

        Returns:
            The corresponding EnumExecutionStatus value

        Raises:
            ValueError: If base_status cannot be mapped to execution status
        """
        from omnibase_core.enums.enum_base_status import EnumBaseStatus

        mapping = {
            EnumBaseStatus.PENDING: cls.PENDING,
            EnumBaseStatus.RUNNING: cls.RUNNING,
            EnumBaseStatus.COMPLETED: cls.COMPLETED,
            EnumBaseStatus.FAILED: cls.FAILED,
            EnumBaseStatus.INACTIVE: cls.CANCELLED,
            EnumBaseStatus.ACTIVE: cls.RUNNING,
            EnumBaseStatus.UNKNOWN: cls.PENDING,
        }

        if base_status in mapping:
            return mapping[base_status]

        raise ValueError(  # error-ok: standard enum conversion error pattern
            f"Cannot convert {base_status} to EnumExecutionStatus"
        )

    @classmethod
    def is_terminal(cls, status: EnumExecutionStatus) -> bool:
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
    def is_active(cls, status: EnumExecutionStatus) -> bool:
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
    def is_successful(cls, status: EnumExecutionStatus) -> bool:
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
    def is_failure(cls, status: EnumExecutionStatus) -> bool:
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
    def is_skipped(cls, status: EnumExecutionStatus) -> bool:
        """
        Check if the status indicates the execution was skipped.

        Args:
            status: The status to check

        Returns:
            True if skipped, False otherwise
        """
        return status == cls.SKIPPED

    @classmethod
    def is_running(cls, status: EnumExecutionStatus) -> bool:
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
    def is_cancelled(cls, status: EnumExecutionStatus) -> bool:
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
    def is_partial(cls, status: EnumExecutionStatus) -> bool:
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
