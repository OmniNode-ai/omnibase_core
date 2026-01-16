"""
Protocol for Logger-Like Objects.

Provides a structural typing protocol for objects that support logging
via info() and warning() methods, enabling duck typing without requiring inheritance.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)

.. versionchanged:: 0.6.3
    Added warning() method for proper log level support (OMN-1150)
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolLoggerLike(Protocol):
    """
    Protocol for loggers with info() and warning() methods.

    This protocol enables duck typing for loggers - any object with compatible
    info() and warning() methods can be used without requiring inheritance from
    a specific class.

    This is useful for accepting various logger implementations (stdlib logging,
    structlog, custom loggers) without coupling to a specific implementation.

    Example:
        >>> import logging
        >>> from omnibase_core.protocols.protocol_logger_like import ProtocolLoggerLike
        >>>
        >>> def log_message(logger: ProtocolLoggerLike, msg: str) -> None:
        ...     logger.info(msg)
        >>>
        >>> def log_warning(logger: ProtocolLoggerLike, msg: str, user_id: str) -> None:
        ...     logger.warning(msg, extra={"user_id": user_id, "action": "warn"})
        >>>
        >>> # Works with stdlib logger
        >>> log_message(logging.getLogger(), "Hello")
        >>> log_warning(logging.getLogger(), "Potential issue", user_id="user-123")
    """

    def info(self, message: str, *, extra: dict[str, object] | None = None) -> None:
        """
        Log an info message with optional extra context.

        Args:
            message: The log message to emit
            extra: Optional dictionary of extra context to include
        """
        ...

    def warning(self, message: str, *, extra: dict[str, object] | None = None) -> None:
        """
        Log a warning message with optional extra context.

        Args:
            message: The log message to emit
            extra: Optional dictionary of extra context to include

        .. versionadded:: 0.6.3
            Added for proper warning log level support (OMN-1150)
        """
        ...


__all__ = ["ProtocolLoggerLike"]
