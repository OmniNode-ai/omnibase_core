"""
Enum for event delivery modes.

Defines the available modes for event delivery in the ONEX system.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDeliveryMode(StrValueHelper, str, Enum):
    """
    Enumeration of event delivery modes.

    These modes determine how events are delivered from CLI to nodes.
    """

    DIRECT = "direct"
    INMEMORY = "inmemory"


__all__ = ["EnumDeliveryMode"]
