from enum import Enum


class EnumRegistryHealthStatus(str, Enum):
    """Standard registry health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"
    INITIALIZING = "initializing"
    MAINTENANCE = "maintenance"
    CRITICAL = "critical"
