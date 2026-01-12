"""Discovery sources for node location in ONEX."""

from enum import Enum, unique


@unique
class EnumDiscoverySource(str, Enum):
    """Sources for node discovery in ONEX."""

    REGISTRY = "registry"
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    CACHE = "cache"
    MANUAL = "manual"
