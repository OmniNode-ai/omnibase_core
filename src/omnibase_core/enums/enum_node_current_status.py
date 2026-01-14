"""
Node Current Status Enum

Enumeration for current operational status of nodes.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNodeCurrentStatus(StrValueHelper, str, Enum):
    """Current operational status of a node"""

    READY = "ready"
    BUSY = "busy"
    DEGRADED = "degraded"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"


__all__ = ["EnumNodeCurrentStatus"]
