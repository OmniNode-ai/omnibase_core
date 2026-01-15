"""
ONEX-compatible device type enumeration.

Defines device types for distributed agent orchestration
and deployment strategies.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDeviceType(StrValueHelper, str, Enum):
    """Device type enumeration for distributed systems."""

    MAC_STUDIO = "mac_studio"
    MACBOOK_AIR = "macbook_air"
    MAC_MINI = "mac_mini"
    GENERIC_MAC = "generic_mac"
    LINUX_SERVER = "linux_server"
    WINDOWS_SERVER = "windows_server"
    DOCKER_CONTAINER = "docker_container"
    KUBERNETES_POD = "kubernetes_pod"
    CLOUD_INSTANCE = "cloud_instance"
    UNKNOWN = "unknown"


@unique
class EnumDeviceLocation(StrValueHelper, str, Enum):
    """Device location enumeration for network routing."""

    HOME = "at_home"
    REMOTE = "remote"
    OFFICE = "office"
    CLOUD = "cloud"
    EDGE = "edge"
    UNKNOWN = "unknown"


@unique
class EnumDeviceStatus(StrValueHelper, str, Enum):
    """Device status enumeration for health monitoring."""

    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@unique
class EnumAgentHealth(StrValueHelper, str, Enum):
    """Agent health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"


@unique
class EnumPriority(StrValueHelper, str, Enum):
    """[Any]priority enumeration for agent orchestration."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


@unique
class EnumRoutingStrategy(StrValueHelper, str, Enum):
    """Routing strategy enumeration for agent selection."""

    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    CLOSEST = "closest"
    FASTEST = "fastest"
    RANDOM = "random"
    CAPABILITY_MATCH = "capability_match"


__all__ = ["EnumDeviceType"]
