"""
Validation severity enumeration.
"""

from __future__ import annotations

from enum import Enum


class EnumValidationSeverity(str, Enum):
    """Validation error severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
