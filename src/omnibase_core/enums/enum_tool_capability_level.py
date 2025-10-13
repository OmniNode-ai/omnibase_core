from enum import Enum


class EnumToolCapabilityLevel(str, Enum):
    """Tool capability levels."""

    BASIC = "basic"
    ADVANCED = "advanced"
    ENTERPRISE = "enterprise"
    EXPERIMENTAL = "experimental"
