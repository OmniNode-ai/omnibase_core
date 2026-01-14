"""
Version Status Enums.

Version lifecycle status values.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumVersionStatus(StrValueHelper, str, Enum):
    """Version lifecycle status values."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BETA = "beta"
    ALPHA = "alpha"
    END_OF_LIFE = "end_of_life"


__all__ = ["EnumVersionStatus"]
