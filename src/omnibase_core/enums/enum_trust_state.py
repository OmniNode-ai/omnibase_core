from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTrustState(StrValueHelper, str, Enum):
    UNTRUSTED = "untrusted"
    TRUSTED = "trusted"
    VERIFIED = "verified"


__all__ = ["EnumTrustState"]
