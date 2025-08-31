# DEPRECATED: Use ModelErrorSeverity in model_error_severity.py
# This file is retained for backward compatibility only.

"""
Error Severity Enum

Severity levels for validation errors and system errors.
"""

from enum import Enum


class EnumErrorSeverity(Enum):
    """
    Severity levels for validation errors and system errors.

    Used to categorize the impact and urgency of different types of errors.
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"

    def __str__(self) -> str:
        """Return the string value of the severity."""
        return self.value

    def is_blocking(self) -> bool:
        """Check if this severity level should block execution."""
        return self in [self.ERROR, self.CRITICAL, self.FATAL]

    def is_critical_or_above(self) -> bool:
        """Check if this is critical or fatal severity."""
        return self in [self.CRITICAL, self.FATAL]

    def get_numeric_value(self) -> int:
        """Get numeric value for comparison (higher = more severe)."""
        severity_map = {
            self.DEBUG: 10,
            self.INFO: 20,
            self.WARNING: 30,
            self.ERROR: 40,
            self.CRITICAL: 50,
            self.FATAL: 60,
        }
        return severity_map[self]

    def __lt__(self, other: "EnumErrorSeverity") -> bool:
        """Enable severity comparison."""
        return self.get_numeric_value() < other.get_numeric_value()

    def __le__(self, other: "EnumErrorSeverity") -> bool:
        """Enable severity comparison."""
        return self.get_numeric_value() <= other.get_numeric_value()

    def __gt__(self, other: "EnumErrorSeverity") -> bool:
        """Enable severity comparison."""
        return self.get_numeric_value() > other.get_numeric_value()

    def __ge__(self, other: "EnumErrorSeverity") -> bool:
        """Enable severity comparison."""
        return self.get_numeric_value() >= other.get_numeric_value()
