from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRegistryHealthStatus(StrValueHelper, str, Enum):
    """Standard registry health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"
    INITIALIZING = "initializing"
    MAINTENANCE = "maintenance"
    CRITICAL = "critical"


__all__ = ["EnumRegistryHealthStatus"]
