"""
Enum for event delivery modes.

Defines the available modes for event delivery in the ONEX system.
"""

from enum import Enum


class EnumDeliveryMode(str, Enum):
    """
    Enumeration of event delivery modes.

    These modes determine how events are delivered from CLI to nodes.
    """

    DIRECT = "direct"
    INMEMORY = "inmemory"
