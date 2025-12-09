"""
ONEX-compatible device type enumeration.

Defines device types for distributed agent orchestration
and deployment strategies.
"""

from enum import Enum


class EnumDeviceType(str, Enum):
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


class EnumDeviceLocation(str, Enum):
    """Device location enumeration for network routing."""

    HOME = "at_home"
    REMOTE = "remote"
    OFFICE = "office"
    CLOUD = "cloud"
    EDGE = "edge"
    UNKNOWN = "unknown"


class EnumDeviceStatus(str, Enum):
    """Device status enumeration for health monitoring."""

    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class EnumAgentHealth(str, Enum):
    """Agent health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"


class EnumPriority(str, Enum):
    """[Any]priority enumeration for agent orchestration."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class EnumRoutingStrategy(str, Enum):
    """Routing strategy enumeration for agent selection."""

    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    CLOSEST = "closest"
    FASTEST = "fastest"
    RANDOM = "random"
    CAPABILITY_MATCH = "capability_match"
