"""
Enum for MCP operation status values.
"""

from enum import Enum


class EnumMcpStatus(str, Enum):
    """Status values for MCP operations."""

    SUCCESS = "success"
    ERROR = "error"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RUNNING = "running"
    UNKNOWN = "unknown"
    UNREACHABLE = "unreachable"
