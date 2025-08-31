"""
Enum for alert severity levels.

Defines severity levels for system alerts.
"""

from enum import Enum


class EnumAlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"
