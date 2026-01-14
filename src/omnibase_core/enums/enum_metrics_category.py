"""
Metrics Category Enum.

Strongly typed metrics category values for organizing metric collections.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMetricsCategory(StrValueHelper, str, Enum):
    """Strongly typed metrics category values."""

    GENERAL = "general"
    PERFORMANCE = "performance"
    SYSTEM = "system"
    BUSINESS = "business"
    ANALYTICS = "analytics"
    PROGRESS = "progress"
    CUSTOM = "custom"


# Export for use
__all__ = ["EnumMetricsCategory"]
