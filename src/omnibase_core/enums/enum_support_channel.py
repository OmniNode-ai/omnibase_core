"""Support channel classification for customer interactions."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSupportChannel(StrValueHelper, str, Enum):
    """Support channel through which a customer contacted support.

    Used to track the communication channel for support tickets
    and to apply channel-specific routing or handling rules.
    """

    EMAIL = "email"
    CHAT = "chat"
    WEB = "web"


__all__ = ["EnumSupportChannel"]
