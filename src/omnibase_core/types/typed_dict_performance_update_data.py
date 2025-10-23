from __future__ import annotations

from typing import TypedDict

"""
Typed structure for performance data updates.
"""


class TypedDictPerformanceUpdateData(TypedDict, total=False):
    """Typed structure for performance data updates."""

    average_execution_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    throughput_ops_per_sec: float


__all__ = ["TypedDictPerformanceUpdateData"]
