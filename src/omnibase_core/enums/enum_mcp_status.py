"""
Enum for MCP operation status values.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMCPStatus(StrValueHelper, str, Enum):
    """Status values for MCP operations."""

    SUCCESS = "success"
    ERROR = "error"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RUNNING = "running"
    UNKNOWN = "unknown"
    UNREACHABLE = "unreachable"


__all__ = ["EnumMCPStatus"]
