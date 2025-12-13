"""
TypedDict definition for active status summary.

Strongly-typed structure for active status summary methods.
"""

from typing import TypedDict


class TypedDictActiveSummary(TypedDict):
    """Typed structure for active status summary."""

    status_type: str
    uptime_seconds: int
    uptime_days: float
    uptime_hours: float
    uptime_minutes: float
    last_heartbeat: str
    is_recent_heartbeat: bool
    health_score: float


__all__ = [
    "TypedDictActiveSummary",
]
