"""TypedDict for performance targets configuration."""

from __future__ import annotations

from typing import TypedDict


class TypedDictPerformanceTargets(TypedDict, total=False):
    """Performance targets for success metrics.

    Defines performance thresholds with integer values
    typically representing milliseconds or counts.
    """

    latency_ms: int
    response_time_ms: int
    processing_time_ms: int
    timeout_ms: int
    max_retries: int


__all__ = ["TypedDictPerformanceTargets"]
