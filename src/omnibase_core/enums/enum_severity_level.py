# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Severity level enumeration for messages and notifications (RFC 5424 compliant).

DOCUMENTED EXCEPTION per ADR-006 Status Taxonomy (OMN-1311):
    This enum is intentionally NOT merged into the canonical EnumSeverity because:

    1. **RFC 5424 Compliance**: This enum follows the RFC 5424 syslog severity levels
       which define 11 distinct values (EMERGENCY through TRACE). The canonical
       EnumSeverity has only 5 values (DEBUG through CRITICAL).

    2. **Syslog Integration**: This enum is used for structured logging systems
       that require RFC 5424 compliant severity levels for interoperability with
       syslog, journald, and other logging infrastructure.

    3. **Extended Level Support**: Includes levels not in the canonical enum:
       EMERGENCY, ALERT, NOTICE, TRACE, WARN (alias)

For general-purpose severity classification, use EnumSeverity instead:
    from omnibase_core.enums.enum_severity import EnumSeverity

This enum provides strongly typed severity levels for error messages, warnings,
and logging. Follows ONEX one-enum-per-file naming conventions.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

# Module-level constant for numeric severity levels (avoids per-call dict allocation)
# Compatible with RFC 5424 severity levels with numeric ordering
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
    """

    # Standard severity levels (RFC 5424 inspired)
    EMERGENCY = "emergency"  # System is unusable
    ALERT = "alert"  # Action must be taken immediately
    CRITICAL = "critical"  # Critical conditions
    ERROR = "error"  # Error conditions
    WARNING = "warning"  # Warning conditions
    NOTICE = "notice"  # Normal but significant conditions
    INFO = "info"  # Informational messages
    DEBUG = "debug"  # Debug-level messages

    # Additional common levels
    TRACE = "trace"  # Very detailed debug information
    FATAL = "fatal"  # Fatal error (alias for EMERGENCY)
    WARN = "warn"  # Short form of WARNING

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
