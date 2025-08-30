"""
Enum for incident status states.

Incident status states for monitoring.
"""

from enum import Enum


class EnumIncidentStatus(str, Enum):
    """Incident status states."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"
