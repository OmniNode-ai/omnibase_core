"""
Mapping Type Enum.

Canonical enum for mapping types used in event field transformations.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMappingType(StrValueHelper, str, Enum):
    """Canonical mapping types for event field transformations."""

    DIRECT = "direct"
    TRANSFORM = "transform"
    CONDITIONAL = "conditional"
    COMPOSITE = "composite"


__all__ = ["EnumMappingType"]
