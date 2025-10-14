"""
Contract Performance Metrics TypedDict.

Lightweight type definition for fast import performance monitoring.
Uses TypedDict for zero overhead and dict compatibility.
"""

from typing import Literal, TypedDict


class TypedDictPerformanceMetrics(TypedDict):
    """
    Performance metrics for fast import system.

    Returns dict structure with zero overhead - no Pydantic validation needed.
    """

    module_load_time_ms: float
    """Module import time in milliseconds (should be ~0 for fast imports)."""

    factory_access_time_ms: float
    """Time to access factory singleton in milliseconds."""

    status: Literal["optimal", "needs_optimization"]
    """Performance status based on threshold checks."""


__all__ = ["TypedDictPerformanceMetrics"]
