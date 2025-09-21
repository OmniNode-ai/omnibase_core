"""
Node Health Status Enum.

Defines the health states for nodes in the system.
"""

from __future__ import annotations

from enum import Enum


class EnumNodeHealthStatus(Enum):
    """Health status for nodes."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


# Export for use
__all__ = ["EnumNodeHealthStatus"]