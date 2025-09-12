"""
Enum for incident severity levels.

Incident severity levels for monitoring.
"""

from enum import Enum


class EnumIncidentSeverity(str, Enum):
    """Incident severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"
