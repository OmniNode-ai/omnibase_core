from __future__ import annotations

"""
Metadata node complexity enumeration.
"""


from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMetadataNodeComplexity(StrValueHelper, str, Enum):
    """Metadata node complexity enumeration."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ADVANCED = "advanced"


__all__ = ["EnumMetadataNodeComplexity"]
