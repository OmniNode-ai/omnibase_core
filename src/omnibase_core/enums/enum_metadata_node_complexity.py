"""
Metadata node complexity enumeration.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumMetadataNodeComplexity(str, Enum):
    """Metadata node complexity enumeration."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ADVANCED = "advanced"


__all__ = ["EnumMetadataNodeComplexity"]
