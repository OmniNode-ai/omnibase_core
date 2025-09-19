"""
Complexity level classification enum for nodes.

Defines complexity levels used for categorizing nodes based on their
computational complexity, resource requirements, and operational difficulty.
"""

from enum import Enum


class EnumComplexityLevel(str, Enum):
    """Node complexity level classifications."""

    # Basic complexity levels
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    BASIC = "basic"
    MODERATE = "moderate"
    INTERMEDIATE = "intermediate"
    COMPLEX = "complex"
    ADVANCED = "advanced"
    EXPERT = "expert"

    # Special complexity categories
    CRITICAL = "critical"
    EXPERIMENTAL = "experimental"
    LEGACY = "legacy"

    # Resource-based complexity
    LOW_RESOURCE = "low_resource"
    HIGH_RESOURCE = "high_resource"
    MEMORY_INTENSIVE = "memory_intensive"
    CPU_INTENSIVE = "cpu_intensive"
    IO_INTENSIVE = "io_intensive"

    # Unknown/default
    UNKNOWN = "unknown"
