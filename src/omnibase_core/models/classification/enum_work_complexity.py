"""
Enum for work complexity levels.

Defines the complexity levels for work items.
"""

from enum import Enum


class EnumWorkComplexity(str, Enum):
    """Complexity levels for work items."""

    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"
