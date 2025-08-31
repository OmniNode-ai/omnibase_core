# DEPRECATED: Use ModelValidationSeverity in model_validation_severity.py
# This file is retained for backward compatibility only.

from enum import Enum


class EnumValidationSeverity(str, Enum):
    """Validation issue severity levels"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"

    def __str__(self) -> str:
        return self.value

    def is_blocking(self) -> bool:
        """Check if this severity level blocks operation"""
        return self in [self.ERROR, self.CRITICAL, self.FATAL]

    def is_critical(self) -> bool:
        """Check if this is a critical severity"""
        return self in [self.CRITICAL, self.FATAL]

    def get_numeric_value(self) -> int:
        """Get numeric value for severity comparison"""
        severity_values = {
            self.DEBUG: 0,
            self.INFO: 10,
            self.WARNING: 20,
            self.ERROR: 30,
            self.CRITICAL: 40,
            self.FATAL: 50,
        }
        return severity_values[self]

    def __lt__(self, other):
        """Enable severity comparison"""
        if isinstance(other, EnumValidationSeverity):
            return self.get_numeric_value() < other.get_numeric_value()
        return NotImplemented

    def __le__(self, other):
        """Enable severity comparison"""
        if isinstance(other, EnumValidationSeverity):
            return self.get_numeric_value() <= other.get_numeric_value()
        return NotImplemented
