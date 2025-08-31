"""
Health status enum for LLM provider operations and system components.

Provides strongly-typed health status values for provider health checks
and monitoring with proper ONEX enum naming conventions.
"""

from enum import Enum


class EnumHealthStatus(str, Enum):
    """Health status for LLM provider health checks and system components."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
    WARNING = "warning"
    UNREACHABLE = "unreachable"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"

    def __str__(self) -> str:
        """Return the string value of the health status."""
        return self.value

    def is_operational(self) -> bool:
        """Check if the service is operational despite potential issues."""
        return self in [self.HEALTHY, self.DEGRADED]

    def requires_attention(self) -> bool:
        """Check if this status requires immediate attention."""
        return self in [self.UNHEALTHY, self.CRITICAL]
