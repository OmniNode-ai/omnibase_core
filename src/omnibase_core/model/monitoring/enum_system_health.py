"""
Enum for system health status.

Defines system health status levels.
"""

from enum import Enum


class EnumSystemHealth(str, Enum):
    """System health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
