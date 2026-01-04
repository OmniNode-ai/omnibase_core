"""Regex timeout error for ReDoS protection.

This module provides the RegexTimeoutError exception class used to signal
when a regex operation exceeds the configured timeout limit.
"""

from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class RegexTimeoutError(ModelOnexError):
    """Raised when a regex operation times out.

    This exception is used to signal that a regex search exceeded the
    configured timeout, which may indicate a ReDoS attack or an
    unexpectedly complex pattern. Inherits from ModelOnexError for
    consistent error handling throughout the ONEX framework.

    Example:
        >>> from omnibase_core.errors.error_regex_timeout import (
        ...     RegexTimeoutError,
        ... )
        >>> raise RegexTimeoutError("Regex timed out after 5 seconds")
        Traceback (most recent call last):
            ...
        RegexTimeoutError: [ONEX_CORE_088_TIMEOUT] Regex timed out after 5 seconds
    """

    def __init__(
        self,
        message: str,
        pattern: str | None = None,
        timeout_seconds: float | None = None,
        **context: Any,
    ) -> None:
        """Initialize a RegexTimeoutError.

        Args:
            message: Human-readable error message describing the timeout.
            pattern: The regex pattern that caused the timeout (optional).
            timeout_seconds: The timeout duration in seconds (optional).
            **context: Additional context information passed to ModelOnexError.
        """
        # Add regex-specific context
        if pattern is not None:
            context["pattern"] = pattern
        if timeout_seconds is not None:
            context["timeout_seconds"] = timeout_seconds

        super().__init__(
            message=message,
            error_code=EnumCoreErrorCode.TIMEOUT,
            **context,
        )
