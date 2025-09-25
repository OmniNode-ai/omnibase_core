"""
Registry Status Enum.

Strongly typed status values for registry operations.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumRegistryStatus(str, Enum):
    """Strongly typed registry status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    INITIALIZING = "initializing"
    MAINTENANCE = "maintenance"


# Export for use
__all__ = ["EnumRegistryStatus"]
