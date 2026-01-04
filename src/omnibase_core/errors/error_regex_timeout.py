"""Regex timeout error for ReDoS protection.

This module provides the RegexTimeoutError exception class used to signal
when a regex operation exceeds the configured timeout limit.
"""


class RegexTimeoutError(Exception):
    """Raised when a regex operation times out.

    This exception is used to signal that a regex search exceeded the
    configured timeout, which may indicate a ReDoS attack or an
    unexpectedly complex pattern.

    Example:
        >>> from omnibase_core.errors.error_regex_timeout import (
        ...     RegexTimeoutError,
        ... )
        >>> raise RegexTimeoutError("Regex timed out after 5 seconds")
        Traceback (most recent call last):
            ...
        RegexTimeoutError: Regex timed out after 5 seconds
    """
