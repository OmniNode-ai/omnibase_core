from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumToolRegistrationStatus(StrValueHelper, str, Enum):
    """Status of tool registration."""

    REGISTERED = "registered"
    PENDING = "pending"
    FAILED = "failed"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


__all__ = ["EnumToolRegistrationStatus"]
