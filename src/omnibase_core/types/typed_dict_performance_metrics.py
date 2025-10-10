"""
TypedDict for performance metrics.

Strongly-typed representation for performance measurement results.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict


class TypedDictPerformanceMetrics(TypedDict):
    """Strongly-typed structure for performance measurement results."""

    module_load_time_ms: float
    factory_access_time_ms: float
    status: str


__all__ = ["TypedDictPerformanceMetrics"]
