"""
Complexity enumeration for operations and functions.

Provides strongly typed complexity values for performance estimation.
Follows ONEX one-enum-per-file naming conventions.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumComplexity(StrValueHelper, str, Enum):
    """
    Strongly typed complexity levels for operations.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"

    @classmethod
    def get_estimated_runtime_seconds(cls, complexity: EnumComplexity) -> float:
        """Get estimated runtime in seconds based on complexity."""
        runtime_map = {
            cls.SIMPLE: 0.1,
            cls.MODERATE: 1.0,
            cls.COMPLEX: 10.0,
            cls.VERY_COMPLEX: 60.0,
        }
        return runtime_map.get(complexity, 1.0)

    @classmethod
    def requires_monitoring(cls, complexity: EnumComplexity) -> bool:
        """Check if complexity level requires enhanced monitoring."""
        return complexity in {cls.COMPLEX, cls.VERY_COMPLEX}

    @classmethod
    def allows_parallel_execution(cls, complexity: EnumComplexity) -> bool:
        """Check if complexity allows safe parallel execution."""
        return complexity in {cls.SIMPLE, cls.MODERATE}


# Export for use
__all__ = ["EnumComplexity"]
