"""
Performance impact enumeration for node capabilities and operations.

Strongly typed enumeration for performance impact levels replacing magic strings.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumPerformanceImpact(StrValueHelper, str, Enum):
    """Performance impact levels for capabilities and operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    NEGLIGIBLE = "negligible"


__all__ = ["EnumPerformanceImpact"]
