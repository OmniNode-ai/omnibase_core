from enum import Enum


class EnumDiscoverySource(str, Enum):
    """Sources for node discovery in ONEX."""

    REGISTRY = "registry"
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    CACHE = "cache"
    MANUAL = "manual"
