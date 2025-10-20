"""
Node Current Status Enum

Enumeration for current operational status of nodes.
"""

from enum import Enum


class EnumNodeCurrentStatus(str, Enum):
    """Current operational status of a node"""

    READY = "ready"
    BUSY = "busy"
    DEGRADED = "degraded"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
