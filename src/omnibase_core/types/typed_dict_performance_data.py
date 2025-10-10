from __future__ import annotations

from typing import Dict, TypedDict

"""
Typed structure for performance data updates.
"""


from typing import TypedDict


class TypedDictPerformanceData(TypedDict, total=False):
    """Typed structure for performance data updates."""

    average_execution_time_ms: float
    peak_memory_usage_mb: float
    total_invocations: int


__all__ = ["ModelTypedDictPerformanceData"]
