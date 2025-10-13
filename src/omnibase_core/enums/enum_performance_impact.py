from __future__ import annotations

"""
Performance impact enumeration for node capabilities and operations.

Strongly typed enumeration for performance impact levels replacing magic strings.
"""


from enum import Enum, unique


@unique
class EnumPerformanceImpact(str, Enum):
    """Performance impact levels for capabilities and operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    NEGLIGIBLE = "negligible"


__all__ = ["EnumPerformanceImpact"]
