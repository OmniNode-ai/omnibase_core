"""
Health status enum for LLM provider operations and system components.

Provides strongly-typed health status values for provider health checks
and monitoring with proper ONEX enum naming conventions.
"""

from enum import Enum, unique


@unique
class EnumHealthStatus(str, Enum):
    """Canonical health status for all system components.

    This is the single source of truth for health status values across:
    - LLM providers
    - Nodes
    - Services
    - Tools
    - Registries
    - All other system components
    """

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
    INITIALIZING = "initializing"
    DISPOSING = "disposing"

    def __str__(self) -> str:
        """Return the string value of the health status."""
        return self.value

    def is_operational(self) -> bool:
        """Check if the service is operational despite potential issues."""
        return self in [self.HEALTHY, self.DEGRADED, self.AVAILABLE, self.WARNING]

    def requires_attention(self) -> bool:
        """Check if this status requires immediate attention."""
        return self in [self.UNHEALTHY, self.CRITICAL, self.ERROR, self.UNREACHABLE]

    def is_transitional(self) -> bool:
        """Check if this status indicates a transitional state."""
        return self in [self.INITIALIZING, self.DISPOSING]
