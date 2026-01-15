"""
Severity level enumeration for messages and notifications (RFC 5424 based).

DOCUMENTED EXCEPTION per ADR-006 Status Taxonomy (OMN-1311):
    This enum is intentionally NOT merged into the canonical EnumSeverity because:

    1. **RFC 5424 Base**: This enum includes the 8 RFC 5424 syslog severity levels
       (EMERGENCY through DEBUG) plus common extensions (TRACE, FATAL, WARN).
       The canonical EnumSeverity has 6 values (DEBUG through FATAL).

    2. **Syslog Integration**: This enum is used for structured logging systems
       that require RFC 5424 severity levels for interoperability with
       syslog, journald, and other logging infrastructure.

    3. **Extended Level Support**: Includes levels not in the canonical enum:
       EMERGENCY, ALERT, NOTICE (RFC 5424), plus TRACE, WARN (extensions)

For general-purpose severity classification, use EnumSeverity instead:
    from omnibase_core.enums.enum_severity import EnumSeverity

This enum provides strongly typed severity levels for error messages, warnings,
and logging. Follows ONEX one-enum-per-file naming conventions.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

# Module-level constant for numeric severity levels (avoids per-call dict allocation)
# Uses ascending numeric scale (higher = more severe) for comparison operations.
# Note: RFC 5424 uses descending 0-7 scale; this map uses ascending for intuitive comparison.
_SEVERITY_LEVEL_NUMERIC_MAP: dict[str, int] = {
    "trace": 10,
    "debug": 20,
    "info": 30,
    "notice": 35,
    "warning": 40,
    "warn": 40,
    "error": 50,
    "critical": 60,
    "alert": 70,
    "emergency": 80,
    "fatal": 80,
}


@unique
class EnumSeverityLevel(StrValueHelper, str, Enum):
    """
    Strongly typed severity level for messages and logging.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.

    RFC 5424 Compliance:
        The first 8 values (EMERGENCY through DEBUG) correspond to RFC 5424
        severity levels 0-7. Note: RFC 5424 uses "Informational" for level 6;
        this enum uses "INFO" as a common abbreviation.
    """

    # RFC 5424 severity levels (0-7)
    EMERGENCY = "emergency"  # RFC 5424 level 0: System is unusable
    ALERT = "alert"  # RFC 5424 level 1: Action must be taken immediately
    CRITICAL = "critical"  # RFC 5424 level 2: Critical conditions
    ERROR = "error"  # RFC 5424 level 3: Error conditions
    WARNING = "warning"  # RFC 5424 level 4: Warning conditions
    NOTICE = "notice"  # RFC 5424 level 5: Normal but significant conditions
    INFO = "info"  # RFC 5424 level 6: Informational messages
    DEBUG = "debug"  # RFC 5424 level 7: Debug-level messages

    # Extensions beyond RFC 5424
    TRACE = "trace"  # Extension: Very detailed debug information (below DEBUG)
    FATAL = "fatal"  # Extension: Fatal error (semantic alias for EMERGENCY)
    WARN = "warn"  # Extension: Short form of WARNING

    @classmethod
    def from_string(cls, value: str) -> EnumSeverityLevel:
        """Convert string to severity level with fallback handling."""
        # Handle common variations and case insensitivity
        normalized = value.lower().strip()

        # Direct mapping
        for level in cls:
            if level.value == normalized:
                return level

        # Common aliases (note: "warn" is handled by WARN member, not as alias)
        aliases = {
            "err": cls.ERROR,
            "information": cls.INFO,
            "informational": cls.INFO,
            "verbose": cls.DEBUG,
            "low": cls.INFO,
            "medium": cls.WARNING,
            "high": cls.ERROR,
            "severe": cls.CRITICAL,
        }

        if normalized in aliases:
            return aliases[normalized]

        # Default fallback
        return cls.INFO

    @property
    def numeric_level(self) -> int:
        """Get numeric representation for level comparison."""
        return _SEVERITY_LEVEL_NUMERIC_MAP.get(self.value, 30)  # Default to INFO level

    def is_error_level(self) -> bool:
        """Check if this is an error-level severity."""
        return self.numeric_level >= 50

    def is_warning_level(self) -> bool:
        """Check if this is a warning-level severity."""
        return self.numeric_level >= 40

    def is_info_level(self) -> bool:
        """Check if this is an info-level severity."""
        return self.numeric_level >= 30


# Export for use
__all__ = ["EnumSeverityLevel"]
