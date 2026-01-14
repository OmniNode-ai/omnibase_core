"""
Typed structure for performance data updates.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictPerformanceUpdateData(TypedDict, total=False):
    average_execution_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    throughput_ops_per_sec: float


__all__ = ["TypedDictPerformanceUpdateData"]
