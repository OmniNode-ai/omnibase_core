"""
Action Status Enumeration for Action Metadata Tracking.

Provides status values for tracking action lifecycle in orchestrator workflows.
Actions progress through states from creation to completion or failure.

State Machine:
    CREATED -> READY -> RUNNING -> COMPLETED
       |         |         |
       v         v         v
     FAILED   FAILED    FAILED

.. versionadded:: 0.6.5
    Added as part of OMN-1309 to replace hardcoded status strings with enum references.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumActionStatus(StrValueHelper, str, Enum):
    """
    Action status values for action metadata tracking.

    Represents the lifecycle states of an action within orchestrator workflows.
    Inherits from ``str`` for proper JSON serialization - values serialize
    to lowercase strings.

    Attributes:
        CREATED: Initial state when action is constructed but not yet ready.
        READY: Action has been validated and is ready for execution.
        RUNNING: Action execution is currently in progress.
        COMPLETED: Action has completed successfully.
        FAILED: Action has failed with an error.

    Example:
        >>> status = EnumActionStatus.CREATED
        >>> str(status)
        'created'
        >>> import json
        >>> json.dumps({"status": status})
        '{"status": "created"}'

    .. versionadded:: 0.6.5
        Added as part of OMN-1309 to replace hardcoded status strings.
    """

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    def is_terminal(self) -> bool:
        """
        Check if this status represents a terminal state.

        Terminal states indicate the action has finished execution
        and will not transition to any other state.

        Returns:
            True if COMPLETED or FAILED, False otherwise.

        Example:
            >>> EnumActionStatus.COMPLETED.is_terminal()
            True
            >>> EnumActionStatus.RUNNING.is_terminal()
            False
        """
        return self in {EnumActionStatus.COMPLETED, EnumActionStatus.FAILED}

    def is_active(self) -> bool:
        """
        Check if this status represents an active execution state.

        Active states indicate the action is currently being executed.

        Returns:
            True if RUNNING, False otherwise.

        Example:
            >>> EnumActionStatus.RUNNING.is_active()
            True
            >>> EnumActionStatus.READY.is_active()
            False
        """
        return self == EnumActionStatus.RUNNING

    def is_pending(self) -> bool:
        """
        Check if this status represents a pending state.

        Pending states indicate the action has not yet started execution.

        Returns:
            True if CREATED or READY, False otherwise.

        Example:
            >>> EnumActionStatus.CREATED.is_pending()
            True
            >>> EnumActionStatus.RUNNING.is_pending()
            False
        """
        return self in {EnumActionStatus.CREATED, EnumActionStatus.READY}

    def is_successful(self) -> bool:
        """
        Check if this status represents successful completion.

        Returns:
            True if COMPLETED, False otherwise.

        Example:
            >>> EnumActionStatus.COMPLETED.is_successful()
            True
            >>> EnumActionStatus.FAILED.is_successful()
            False
        """
        return self == EnumActionStatus.COMPLETED

    def is_failure(self) -> bool:
        """
        Check if this status represents a failure state.

        Returns:
            True if FAILED, False otherwise.

        Example:
            >>> EnumActionStatus.FAILED.is_failure()
            True
            >>> EnumActionStatus.COMPLETED.is_failure()
            False
        """
        return self == EnumActionStatus.FAILED

    def can_transition_to(self, target: "EnumActionStatus") -> bool:
        """
        Check if transitioning to the target state is valid.

        Valid state transitions:
            - CREATED -> READY (action validated and ready)
            - CREATED -> FAILED (validation failure)
            - READY -> RUNNING (execution started)
            - READY -> FAILED (pre-execution failure)
            - RUNNING -> COMPLETED (successful completion)
            - RUNNING -> FAILED (execution failure)

        Terminal states (COMPLETED, FAILED) cannot transition to any state.

        Args:
            target: The target status to transition to.

        Returns:
            True if the transition is valid, False otherwise.

        Example:
            >>> EnumActionStatus.CREATED.can_transition_to(EnumActionStatus.READY)
            True
            >>> EnumActionStatus.COMPLETED.can_transition_to(EnumActionStatus.RUNNING)
            False
            >>> EnumActionStatus.RUNNING.can_transition_to(EnumActionStatus.COMPLETED)
            True
        """
        return target in _VALID_TRANSITIONS.get(self, set())


# Class-level constant for valid state transitions.
# Defined after the enum class to allow self-referential enum values.
_VALID_TRANSITIONS: dict[EnumActionStatus, set[EnumActionStatus]] = {
    EnumActionStatus.CREATED: {EnumActionStatus.READY, EnumActionStatus.FAILED},
    EnumActionStatus.READY: {EnumActionStatus.RUNNING, EnumActionStatus.FAILED},
    EnumActionStatus.RUNNING: {EnumActionStatus.COMPLETED, EnumActionStatus.FAILED},
    EnumActionStatus.COMPLETED: set(),
    EnumActionStatus.FAILED: set(),
}


__all__ = ["EnumActionStatus"]
