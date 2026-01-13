from enum import Enum, unique


@unique
class EnumToolCapabilityLevel(str, Enum):
    """Tool capability levels."""

    BASIC = "basic"
    ADVANCED = "advanced"
    ENTERPRISE = "enterprise"
    EXPERIMENTAL = "experimental"
