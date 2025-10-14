from __future__ import annotations

"""
Node Health Status Enum.

Defines the health states for nodes in the system.
"""


from enum import Enum, unique


@unique
class EnumNodeHealthStatus(str, Enum):
    """Health status for nodes."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return self.value


# Export for use
__all__ = ["EnumNodeHealthStatus"]
