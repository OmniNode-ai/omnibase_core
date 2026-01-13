"""
Version Status Enums.

Version lifecycle status values.
"""

from enum import Enum, unique


@unique
class EnumVersionStatus(str, Enum):
    """Version lifecycle status values."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BETA = "beta"
    ALPHA = "alpha"
    END_OF_LIFE = "end_of_life"
