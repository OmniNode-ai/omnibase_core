"""
Context position enum for prompt builder tool.

Provides strongly-typed position values for context section injection
with proper ONEX enum naming conventions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumContextPosition(StrValueHelper, str, Enum):
    """Context section positions."""

    BEFORE = "before"
    AFTER = "after"
    REPLACE = "replace"


__all__ = ["EnumContextPosition"]
