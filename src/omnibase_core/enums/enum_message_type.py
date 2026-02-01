from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMessageType(StrValueHelper, str, Enum):
    """Message categories for proper routing and handling."""

    COMMAND = "command"
    DATA = "data"
    NOTIFICATION = "notification"
    QUERY = "query"


__all__ = ["EnumMessageType"]
