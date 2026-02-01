"""
Dispatch Status Enumeration.

Defines status values for message dispatch operations in the runtime dispatch engine.
Used to track the outcome of routing and handler execution.

Thread Safety:
    All enums in this module are immutable and thread-safe.
    Enum values can be safely shared across threads without synchronization.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDispatchStatus(StrValueHelper, str, Enum):
    """
    Status values for dispatch operations.

    Represents the outcome of a message dispatch operation, from initial
    routing through handler execution and result publishing.

    Values:
        SUCCESS: Message was successfully routed, handled, and outputs published
        ROUTED: Message was successfully routed to a handler (not yet executed)
        NO_HANDLER: No handler was registered for the message type/topic
        HANDLER_ERROR: Handler execution failed with an exception
        TIMEOUT: Handler execution exceeded the configured timeout
        INVALID_MESSAGE: Message failed validation before dispatch
        PUBLISH_FAILED: Handler succeeded but output publishing failed
        SKIPPED: Message was intentionally skipped (e.g., filtered, deduplicated)

    Example:
        >>> status = EnumDispatchStatus.SUCCESS
        >>> status.is_terminal()
        True
        >>> EnumDispatchStatus.ROUTED.is_successful()
        False
        >>> str(EnumDispatchStatus.HANDLER_ERROR)
        'handler_error'
    """

    SUCCESS = "success"
    """Message was successfully routed, handled, and outputs published."""

    ROUTED = "routed"
    """Message was successfully routed to a handler (pending execution)."""

    NO_HANDLER = "no_handler"
    """No handler was registered for the message type/topic."""

    HANDLER_ERROR = "handler_error"
    """Handler execution failed with an exception."""

    TIMEOUT = "timeout"
    """Handler execution exceeded the configured timeout."""

    INVALID_MESSAGE = "invalid_message"
    """Message failed validation before dispatch."""

    PUBLISH_FAILED = "publish_failed"
    """Handler succeeded but output publishing failed."""

    SKIPPED = "skipped"
    """Message was intentionally skipped (e.g., filtered, deduplicated)."""

    def is_terminal(self) -> bool:
        """
        Check if this status represents a terminal state.

        Terminal states indicate the dispatch operation has completed
        (either successfully or with a failure).

        Returns:
            True if the status represents a terminal state, False otherwise

        Example:
            >>> EnumDispatchStatus.SUCCESS.is_terminal()
            True
            >>> EnumDispatchStatus.ROUTED.is_terminal()
            False
        """
        return self in {
            EnumDispatchStatus.SUCCESS,
            EnumDispatchStatus.NO_HANDLER,
            EnumDispatchStatus.HANDLER_ERROR,
            EnumDispatchStatus.TIMEOUT,
            EnumDispatchStatus.INVALID_MESSAGE,
            EnumDispatchStatus.PUBLISH_FAILED,
            EnumDispatchStatus.SKIPPED,
        }

    def is_successful(self) -> bool:
        """
        Check if this status represents a successful dispatch.

        Returns:
            True only if status is SUCCESS, False otherwise

        Example:
            >>> EnumDispatchStatus.SUCCESS.is_successful()
            True
            >>> EnumDispatchStatus.ROUTED.is_successful()
            False
        """
        return self == EnumDispatchStatus.SUCCESS

    def is_error(self) -> bool:
        """
        Check if this status represents an error condition.

        Returns:
            True if the status represents an error, False otherwise

        Example:
            >>> EnumDispatchStatus.HANDLER_ERROR.is_error()
            True
            >>> EnumDispatchStatus.SUCCESS.is_error()
            False
        """
        return self in {
            EnumDispatchStatus.NO_HANDLER,
            EnumDispatchStatus.HANDLER_ERROR,
            EnumDispatchStatus.TIMEOUT,
            EnumDispatchStatus.INVALID_MESSAGE,
            EnumDispatchStatus.PUBLISH_FAILED,
        }

    def requires_retry(self) -> bool:
        """
        Check if this status indicates the operation should be retried.

        Only transient failures (timeout, publish_failed) should be retried.
        Permanent failures (no_handler, invalid_message) should not be retried.

        Returns:
            True if the operation should be retried, False otherwise

        Example:
            >>> EnumDispatchStatus.TIMEOUT.requires_retry()
            True
            >>> EnumDispatchStatus.NO_HANDLER.requires_retry()
            False
        """
        return self in {
            EnumDispatchStatus.TIMEOUT,
            EnumDispatchStatus.PUBLISH_FAILED,
        }

    @classmethod
    def get_description(cls, status: "EnumDispatchStatus") -> str:
        """
        Get a human-readable description of the dispatch status.

        Args:
            status: The dispatch status to describe

        Returns:
            A human-readable description of the status

        Example:
            >>> EnumDispatchStatus.get_description(EnumDispatchStatus.SUCCESS)
            'Message was successfully routed, handled, and outputs published'
        """
        descriptions = {
            cls.SUCCESS: "Message was successfully routed, handled, and outputs published",
            cls.ROUTED: "Message was successfully routed to a handler (pending execution)",
            cls.NO_HANDLER: "No handler was registered for the message type/topic",
            cls.HANDLER_ERROR: "Handler execution failed with an exception",
            cls.TIMEOUT: "Handler execution exceeded the configured timeout",
            cls.INVALID_MESSAGE: "Message failed validation before dispatch",
            cls.PUBLISH_FAILED: "Handler succeeded but output publishing failed",
            cls.SKIPPED: "Message was intentionally skipped",
        }
        return descriptions.get(status, "Unknown dispatch status")


__all__ = ["EnumDispatchStatus"]
