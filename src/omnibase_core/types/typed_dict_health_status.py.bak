from __future__ import annotations

"""
TypedDict for health status information.
"""

from datetime import datetime
from typing import TypedDict


class TypedDictHealthStatus(TypedDict):
    """TypedDict for health status information."""

    status: str  # "healthy", "degraded", "unhealthy"
    uptime_seconds: int
    last_check: datetime
    error_count: int
    warning_count: int
    checks_passed: int
    checks_total: int
