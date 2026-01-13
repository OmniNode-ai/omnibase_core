from enum import Enum, unique


@unique
class EnumMessageType(str, Enum):
    """Message categories for proper routing and handling."""

    COMMAND = "command"
    DATA = "data"
    NOTIFICATION = "notification"
    QUERY = "query"
