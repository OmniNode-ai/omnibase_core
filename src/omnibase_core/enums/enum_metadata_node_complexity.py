"""
Metadata node complexity enumeration.
"""

from enum import Enum


class EnumMetadataNodeComplexity(str, Enum):
    """Metadata node complexity enumeration."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ADVANCED = "advanced"
