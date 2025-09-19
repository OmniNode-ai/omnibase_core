"""
Registry Status Enum.

Strongly typed status values for registry operations.
"""

from enum import Enum


class EnumRegistryStatus(str, Enum):
    """Strongly typed registry status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    INITIALIZING = "initializing"
    MAINTENANCE = "maintenance"


# Export for use
__all__ = ["EnumRegistryStatus"]
