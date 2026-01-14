"""Severity levels for logging, errors, and diagnostic messages."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSeverity(StrValueHelper, str, Enum):
    """Severity classification for system messages and events.

    Provides a standard severity scale from DEBUG (lowest) to FATAL (highest)
    for consistent categorization across logging, error handling, and diagnostics.

    Severity Levels (lowest to highest):
        DEBUG: Detailed diagnostic information for debugging.
        INFO: General operational information.
        WARNING: Unexpected situation that doesn't prevent operation.
        ERROR: Operation failed but system can continue.
        CRITICAL: Serious error requiring attention, system can continue degraded.
        FATAL: Unrecoverable error, system must terminate or cannot proceed.

    CRITICAL vs FATAL:
        Use CRITICAL when the error is severe but the system can still function
        (e.g., a subsystem failure that doesn't affect other operations).
        Use FATAL when the error makes continued operation impossible or unsafe
        (e.g., corrupted state, missing critical resources, security breach).
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


__all__ = ["EnumSeverity"]
