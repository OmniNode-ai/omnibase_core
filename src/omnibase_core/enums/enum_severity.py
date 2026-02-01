"""Severity levels for logging, errors, and diagnostic messages."""

from enum import Enum, unique

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.utils.util_str_enum_base import StrValueHelper

# Module-level constant for numeric severity levels (avoids per-call dict allocation)
# Ordering: DEBUG(10) < INFO(20) < WARNING(30) < ERROR(40) < CRITICAL(50) < FATAL(60)
_SEVERITY_NUMERIC_MAP: dict[str, int] = {
    "debug": 10,
    "info": 20,
    "warning": 30,
    "error": 40,
    "critical": 50,
    "fatal": 60,
}


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

    Numeric Levels:
        Each severity has an associated numeric level for comparison:
        DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50, FATAL=60
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"

    @classmethod
    def from_string(cls, value: str) -> "EnumSeverity":
        """Convert string to severity level.

        Args:
            value: String representation of severity (case-insensitive).

        Returns:
            The corresponding EnumSeverity member.

        Raises:
            ModelOnexError: If value doesn't match any severity level.
        """
        try:
            return cls(value.lower().strip())
        except ValueError:
            # Lazy import to avoid circular dependency
            from omnibase_core.errors import ModelOnexError

            valid_values = [e.value for e in cls]
            msg = f"Invalid severity: '{value}'. Must be one of: {valid_values}"
            raise ModelOnexError(msg, error_code=EnumCoreErrorCode.VALIDATION_ERROR)

    @property
    def numeric_level(self) -> int:
        """Get numeric representation for severity comparison.

        Returns:
            Numeric level: DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50, FATAL=60.
            Defaults to INFO level (20) for unknown values (defensive fallback).
        """
        return _SEVERITY_NUMERIC_MAP.get(self.value, 20)

    def is_error_or_above(self) -> bool:
        """Check if this severity is ERROR level or higher.

        Returns:
            True if severity is ERROR, CRITICAL, or FATAL.
        """
        return self.numeric_level >= 40

    def is_warning_or_above(self) -> bool:
        """Check if this severity is WARNING level or higher.

        Returns:
            True if severity is WARNING, ERROR, CRITICAL, or FATAL.
        """
        return self.numeric_level >= 30


__all__ = ["EnumSeverity"]
