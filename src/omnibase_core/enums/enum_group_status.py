from enum import Enum, unique


@unique
class EnumGroupStatus(str, Enum):
    """Group lifecycle status values."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    MAINTENANCE = "maintenance"
