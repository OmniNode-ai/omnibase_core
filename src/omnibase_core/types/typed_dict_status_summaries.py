"""
TypedDict definitions for node status summary return types.

Strongly-typed structures for status summary methods.
"""

from typing import TypedDict


class TypedDictMaintenanceSummary(TypedDict):
    """Typed structure for maintenance status summary."""

    status_type: str
    estimated_completion: str
    maintenance_reason: str
    is_critical: bool
    is_scheduled: bool
    priority: str


class TypedDictErrorSummary(TypedDict):
    """Typed structure for error status summary."""

    status_type: str
    error_code: str
    error_message: str
    has_recovery_suggestion: bool
    recovery_suggestion: str | None
    is_critical: bool
    severity: str


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
    "TypedDictMaintenanceSummary",
    "TypedDictErrorSummary",
    "TypedDictActiveSummary",
]
