from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumServiceHealthStatus(StrValueHelper, str, Enum):
    """Standard service health status values."""

    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    ERROR = "error"
    DEGRADED = "degraded"
    TIMEOUT = "timeout"
    AUTHENTICATING = "authenticating"
    MAINTENANCE = "maintenance"


__all__ = ["EnumServiceHealthStatus"]
