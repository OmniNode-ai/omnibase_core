"""
TypedDict definition for maintenance status summary.

Strongly-typed structure for maintenance status summary methods.
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


__all__ = [
    "TypedDictMaintenanceSummary",
]
