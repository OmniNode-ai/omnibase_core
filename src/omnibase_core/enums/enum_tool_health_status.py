"""
Tool Health Status Enums.

Health status values for tool monitoring.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumToolHealthStatus(StrValueHelper, str, Enum):
    """Tool health status values for monitoring and reporting."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


__all__ = ["EnumToolHealthStatus"]
