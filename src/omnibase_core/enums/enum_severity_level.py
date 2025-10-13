from __future__ import annotations

"""
Severity level enumeration for messages and notifications.

Provides strongly typed severity levels for error messages, warnings, and logging.
Follows ONEX one-enum-per-file naming conventions.
"""


from enum import Enum, unique


@unique
class EnumSeverityLevel(str, Enum):
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

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def from_string(cls, value: str) -> EnumSeverityLevel:
        """Convert string to severity level with fallback handling."""
        # Handle common variations and case insensitivity
        normalized = value.lower().strip()

        # Direct mapping
        for level in cls:
            if level.value == normalized:
                return level

        # Common aliases
        aliases = {
            "err": cls.ERROR,
            "warn": cls.WARNING,
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
        # Severity level classification - architectural design for logging levels
        levels = {
            self.TRACE: 10,
            self.DEBUG: 20,
            self.INFO: 30,
            self.NOTICE: 35,
            self.WARNING: 40,
            self.WARN: 40,
            self.ERROR: 50,
            self.CRITICAL: 60,
            self.ALERT: 70,
            self.EMERGENCY: 80,
            self.FATAL: 80,
        }
        return levels.get(self, 30)  # Default to INFO level

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
