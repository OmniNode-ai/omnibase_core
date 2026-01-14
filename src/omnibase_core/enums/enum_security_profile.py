from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSecurityProfile(StrValueHelper, str, Enum):
    """Security profile levels for progressive security implementation."""

    SP0_BOOTSTRAP = "SP0_BOOTSTRAP"
    SP1_BASELINE = "SP1_BASELINE"
    SP2_PRODUCTION = "SP2_PRODUCTION"
    SP3_HIGH_ASSURANCE = "SP3_HIGH_ASSURANCE"


__all__ = ["EnumSecurityProfile"]
