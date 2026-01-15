"""
Operational complexity enumeration for performance and execution characteristics.

Focused on runtime, resource usage, and operational concerns.
Part of the unified complexity enum consolidation strategy.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumOperationalComplexity(StrValueHelper, str, Enum):
    """
    Operational complexity levels for runtime and execution characteristics.

    Focuses on performance implications, resource usage, and operational concerns
    rather than conceptual difficulty or skill requirements.
    """

    # Execution complexity levels
    MINIMAL = "minimal"  # < 100ms, minimal resources
    LIGHTWEIGHT = "lightweight"  # < 1s, low resources
    STANDARD = "standard"  # < 10s, moderate resources
    INTENSIVE = "intensive"  # < 60s, high resources
    HEAVY = "heavy"  # > 60s, very high resources

    @classmethod
    def get_estimated_runtime_seconds(
        cls,
        complexity: EnumOperationalComplexity,
    ) -> float:
        """Get estimated runtime in seconds based on operational complexity."""
        runtime_map = {
            cls.MINIMAL: 0.1,
            cls.LIGHTWEIGHT: 1.0,
            cls.STANDARD: 10.0,
            cls.INTENSIVE: 60.0,
            cls.HEAVY: 300.0,
        }
        return runtime_map.get(complexity, 10.0)

    @classmethod
    def requires_monitoring(cls, complexity: EnumOperationalComplexity) -> bool:
        """Check if operational complexity requires enhanced monitoring."""
        return complexity in {cls.INTENSIVE, cls.HEAVY}

    @classmethod
    def allows_parallel_execution(cls, complexity: EnumOperationalComplexity) -> bool:
        """Check if operational complexity allows safe parallel execution."""
        return complexity in {cls.MINIMAL, cls.LIGHTWEIGHT, cls.STANDARD}

    @classmethod
    def get_resource_category(cls, complexity: EnumOperationalComplexity) -> str:
        """Get resource usage category for operational complexity."""
        resource_map = {
            cls.MINIMAL: "very_low",
            cls.LIGHTWEIGHT: "low",
            cls.STANDARD: "moderate",
            cls.INTENSIVE: "high",
            cls.HEAVY: "very_high",
        }
        return resource_map.get(complexity, "moderate")


# Export for use
__all__ = ["EnumOperationalComplexity"]
