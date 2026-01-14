"""Discovery sources for node location in ONEX."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDiscoverySource(StrValueHelper, str, Enum):
    """Sources for node discovery in ONEX."""

    REGISTRY = "registry"
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    CACHE = "cache"
    MANUAL = "manual"


__all__ = ["EnumDiscoverySource"]
