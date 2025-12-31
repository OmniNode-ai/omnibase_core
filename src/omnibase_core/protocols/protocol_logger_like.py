# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Protocol for Logger-Like Objects.

Provides a structural typing protocol for objects that support logging
via an info() method, enabling duck typing without requiring inheritance.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolLoggerLike(Protocol):
    """
    Protocol for loggers with info() method.

    This protocol enables duck typing for loggers - any object with a compatible
    info() method can be used without requiring inheritance from a specific class.

    This is useful for accepting various logger implementations (stdlib logging,
    structlog, custom loggers) without coupling to a specific implementation.

    Example:
        >>> import logging
        >>> from omnibase_core.protocols.protocol_logger_like import ProtocolLoggerLike
        >>>
        >>> def log_message(logger: ProtocolLoggerLike, msg: str) -> None:
        ...     logger.info(msg)
        >>>
        >>> def log_with_context(logger: ProtocolLoggerLike, msg: str, user_id: str) -> None:
        ...     logger.info(msg, extra={"user_id": user_id, "action": "process"})
        >>>
        >>> # Works with stdlib logger
        >>> log_message(logging.getLogger(), "Hello")
        >>> log_with_context(logging.getLogger(), "Processing request", user_id="user-123")
    """

    def info(self, message: str, *, extra: dict[str, object] | None = None) -> None:
        """
        Log an info message with optional extra context.

        Args:
            message: The log message to emit
            extra: Optional dictionary of extra context to include
        """
        ...


__all__ = ["ProtocolLoggerLike"]
