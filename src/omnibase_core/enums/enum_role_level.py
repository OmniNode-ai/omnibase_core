"""
Enum for role levels.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumRoleLevel(StrValueHelper, str, Enum):
    """Role levels for users."""

    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"
    STAFF = "staff"
    DISTINGUISHED = "distinguished"
    FELLOW = "fellow"


__all__ = ["EnumRoleLevel"]
