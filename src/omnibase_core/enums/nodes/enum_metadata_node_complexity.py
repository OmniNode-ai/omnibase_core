"""
Metadata node complexity enumeration.

Provides strongly typed complexity levels for metadata nodes in ONEX framework.
"""

from enum import Enum


class EnumMetadataNodeComplexity(str, Enum):
    """Complexity levels for metadata nodes."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ADVANCED = "advanced"
