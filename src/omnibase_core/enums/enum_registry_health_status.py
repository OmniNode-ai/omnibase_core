from enum import Enum, unique


@unique
class EnumRegistryHealthStatus(str, Enum):
    """Standard registry health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"
    INITIALIZING = "initializing"
    MAINTENANCE = "maintenance"
    CRITICAL = "critical"
