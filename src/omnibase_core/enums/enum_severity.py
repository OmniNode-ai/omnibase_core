"""Severity levels for violations and issues."""

from enum import Enum


class EnumSeverity(str, Enum):
    """Severity levels for violations."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"
