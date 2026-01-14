"""
Whitespace trim modes for contract-driven NodeCompute.

This module defines the trim modes available for TRIM transformations.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTrimMode(StrValueHelper, str, Enum):
    """
    Whitespace trim modes.

    Attributes:
        BOTH: Trim whitespace from both ends.
        LEFT: Trim whitespace from the left (start) only.
        RIGHT: Trim whitespace from the right (end) only.
    """

    BOTH = "both"
    LEFT = "left"
    RIGHT = "right"


__all__ = ["EnumTrimMode"]
