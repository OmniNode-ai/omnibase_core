from __future__ import annotations

"""
Validation severity enumeration.
"""


from enum import Enum, unique


@unique
class EnumValidationSeverity(str, Enum):
    """Validation error severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


__all__ = ["EnumValidationSeverity"]
