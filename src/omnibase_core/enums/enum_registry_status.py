from __future__ import annotations

"""
Registry Status Enum.

Strongly typed status values for registry operations.
"""


from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRegistryStatus(StrValueHelper, str, Enum):
    """Strongly typed registry status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    INITIALIZING = "initializing"
    MAINTENANCE = "maintenance"


# Export for use
__all__ = ["EnumRegistryStatus"]
