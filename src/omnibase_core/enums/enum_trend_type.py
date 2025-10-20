from __future__ import annotations

"""
Trend type enumeration for trend data models.
"""


from enum import Enum, unique


@unique
class EnumTrendType(str, Enum):
    """
    Enumeration for trend types.

    Provides type-safe options for trend classification.
    """

    METRIC = "metric"
    USAGE = "usage"
    PERFORMANCE = "performance"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    LATENCY = "latency"
    RESOURCE = "resource"
    CUSTOM = "custom"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


# Export for use
__all__ = ["EnumTrendType"]
