from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumToolCapabilityLevel(StrValueHelper, str, Enum):
    """Tool capability levels."""

    BASIC = "basic"
    ADVANCED = "advanced"
    ENTERPRISE = "enterprise"
    EXPERIMENTAL = "experimental"


__all__ = ["EnumToolCapabilityLevel"]
