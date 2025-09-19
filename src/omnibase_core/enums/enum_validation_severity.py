"""
Validation severity enumeration.
"""

from enum import Enum


class EnumValidationSeverity(str, Enum):
    """Validation error severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
