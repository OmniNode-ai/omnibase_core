"""
Metrics Category Enum.

Strongly typed metrics category values for organizing metric collections.
"""

from __future__ import annotations

from enum import Enum


class EnumMetricsCategory(str, Enum):
    """Strongly typed metrics category values."""

    GENERAL = "GENERAL"
    PERFORMANCE = "PERFORMANCE"
    SYSTEM = "SYSTEM"
    BUSINESS = "BUSINESS"
    ANALYTICS = "ANALYTICS"
    PROGRESS = "PROGRESS"
    CUSTOM = "CUSTOM"


# Export for use
__all__ = ["EnumMetricsCategory"]
