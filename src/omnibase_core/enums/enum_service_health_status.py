from enum import Enum


class EnumServiceHealthStatus(str, Enum):
    """Standard service health status values."""

    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    ERROR = "error"
    DEGRADED = "degraded"
    TIMEOUT = "timeout"
    AUTHENTICATING = "authenticating"
    MAINTENANCE = "maintenance"
