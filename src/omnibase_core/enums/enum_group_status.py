from enum import Enum


class EnumGroupStatus(str, Enum):
    """Group lifecycle status values."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    MAINTENANCE = "maintenance"
