"""Severity levels for logging, errors, and diagnostic messages."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSeverity(StrValueHelper, str, Enum):
    """Severity classification for system messages and events.

    Provides a standard severity scale from DEBUG (lowest) to FATAL (highest)
    for consistent categorization across logging, error handling, and diagnostics.
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"
