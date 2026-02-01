"""
TypedDict for legacy dispatch metrics.

Used by MessageDispatchEngine for backwards-compatible metrics tracking.
For structured metrics, use ModelDispatchMetrics instead.
"""

from __future__ import annotations

from typing import TypedDict

__all__ = ["TypedDictLegacyDispatchMetrics"]


class TypedDictLegacyDispatchMetrics(TypedDict):
    """
    TypedDict for legacy dispatch engine metrics.

    Provides backwards-compatible dict format for metrics.
    For structured metrics, use ModelDispatchMetrics instead.
    """

    dispatch_count: int
    dispatch_success_count: int
    dispatch_error_count: int
    total_latency_ms: float
    handler_execution_count: int
    handler_error_count: int
    routes_matched_count: int
    no_handler_count: int
    category_mismatch_count: int
