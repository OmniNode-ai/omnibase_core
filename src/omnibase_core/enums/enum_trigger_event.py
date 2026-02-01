"""
Trigger Event Enumeration.

Trigger events for workflow and checkpoint automation in ONEX infrastructure.
Used by context models to specify what event triggered an action or checkpoint.
"""

from enum import Enum, unique
from functools import cache

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTriggerEvent(StrValueHelper, str, Enum):
    """Enumeration for events that can trigger workflow actions or checkpoints."""

    # Workflow progress triggers
    STAGE_COMPLETE = "stage_complete"  # A workflow stage completed successfully
    STEP_COMPLETE = "step_complete"  # A workflow step completed successfully

    # Error and recovery triggers
    ERROR = "error"  # An error occurred during execution
    TIMEOUT = "timeout"  # A timeout threshold was exceeded

    # Manual and scheduled triggers
    MANUAL = "manual"  # Manually triggered by user or operator
    SCHEDULED = "scheduled"  # Triggered by a scheduled job or cron

    # Threshold-based triggers
    THRESHOLD_EXCEEDED = "threshold_exceeded"  # A metric threshold was exceeded

    # System triggers
    STARTUP = "startup"  # System or service startup
    SHUTDOWN = "shutdown"  # System or service shutdown

    @classmethod
    @cache
    def _automatic_triggers(cls) -> frozenset["EnumTriggerEvent"]:
        """Return cached frozenset of automatic trigger events.

        Uses functools.cache for memoization to avoid recreating the frozenset on each call.
        """
        return frozenset(
            {
                cls.STAGE_COMPLETE,
                cls.STEP_COMPLETE,
                cls.ERROR,
                cls.TIMEOUT,
                cls.SCHEDULED,
                cls.THRESHOLD_EXCEEDED,
                cls.STARTUP,
                cls.SHUTDOWN,
            }
        )

    @classmethod
    @cache
    def _error_triggers(cls) -> frozenset["EnumTriggerEvent"]:
        """Return cached frozenset of error-related trigger events.

        Uses functools.cache for memoization to avoid recreating the frozenset on each call.
        """
        return frozenset({cls.ERROR, cls.TIMEOUT, cls.THRESHOLD_EXCEEDED})

    @classmethod
    def is_automatic(cls, trigger: "EnumTriggerEvent") -> bool:
        """
        Check if the trigger is automatic (not user-initiated).

        Args:
            trigger: The trigger event to check

        Returns:
            True if automatic, False if manual
        """
        return trigger in cls._automatic_triggers()

    @classmethod
    def is_error_related(cls, trigger: "EnumTriggerEvent") -> bool:
        """
        Check if the trigger is related to an error condition.

        Args:
            trigger: The trigger event to check

        Returns:
            True if error-related, False otherwise
        """
        return trigger in cls._error_triggers()
