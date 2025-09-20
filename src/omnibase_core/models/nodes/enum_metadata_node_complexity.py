"""
Metadata Node Complexity Enumeration.

Enumeration defining complexity levels for metadata nodes.
"""

from enum import Enum


class ModelMetadataNodeComplexity(str, Enum):
    """Metadata node complexity enumeration."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ADVANCED = "advanced"


# Export for use
__all__ = ["ModelMetadataNodeComplexity"]