"""
Enum for node status values.

Defines the possible status values for ONEX nodes.
"""

from enum import Enum


class EnumNodeStatus(str, Enum):
    """
    Enumeration of node status values.

    These values represent the operational state of ONEX nodes.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
