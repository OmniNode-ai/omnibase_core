"""
Tool Health Status Enums.

Health status values for tool monitoring.
"""

from enum import Enum


class EnumToolHealthStatus(str, Enum):
    """Tool health status values for monitoring and reporting."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    ERROR = "error"
    UNAVAILABLE = "unavailable"
