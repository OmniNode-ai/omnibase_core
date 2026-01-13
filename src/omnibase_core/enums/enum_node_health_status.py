from __future__ import annotations

"""
Node Health Status Enum.

Defines the health states for nodes in the system.
"""


from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNodeHealthStatus(StrValueHelper, str, Enum):
    """Health status for nodes."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


# Export for use
__all__ = ["EnumNodeHealthStatus"]
