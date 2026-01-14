"""
Tool Status Enums.

Tool lifecycle status values.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumToolStatus(StrValueHelper, str, Enum):
    """Tool lifecycle status values."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    MAINTENANCE = "maintenance"
    END_OF_LIFE = "end_of_life"


__all__ = ["EnumToolStatus"]
