"""
TypedDict for resource usage metrics.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictResourceUsage(TypedDict):
    cpu_percent: float
    memory_mb: float
    disk_usage_mb: float
    network_in_mb: float
    network_out_mb: float
    open_connections: int


__all__ = ["TypedDictResourceUsage"]
