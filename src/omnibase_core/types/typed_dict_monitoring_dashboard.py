"""
TypedDict for performance monitoring dashboard data.

Provides type-safe structure for monitoring dashboard statistics returned by
ProtocolPerformanceMonitor.get_monitoring_dashboard().
"""

from typing import TypedDict


class TypedDictMonitoringDashboard(TypedDict, total=False):
    """
    Type-safe structure for performance monitoring dashboard data.

    This TypedDict uses total=False because the exact structure is
    implementation-defined. Common fields are documented here but
    implementations may include additional fields.

    Attributes:
        total_operations: Total number of tracked operations.
        avg_duration_ms: Average operation duration in milliseconds.
        cache_hit_rate: Percentage of operations with cache hits (0.0-100.0).
        operations_by_type: Breakdown of operations by operation_name.
        error_rate: Percentage of operations that failed (0.0-100.0).
        p50_duration_ms: 50th percentile (median) duration in milliseconds.
        p95_duration_ms: 95th percentile duration in milliseconds.
        p99_duration_ms: 99th percentile duration in milliseconds.

    Example:
        .. code-block:: python

            from omnibase_core.types import TypedDictMonitoringDashboard

            dashboard: TypedDictMonitoringDashboard = {
                "total_operations": 1000,
                "avg_duration_ms": 45.5,
                "cache_hit_rate": 85.0,
            }

    .. versionadded:: 0.4.0
    """

    total_operations: int
    avg_duration_ms: float
    cache_hit_rate: float
    operations_by_type: dict[str, int]
    error_rate: float
    p50_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float


__all__ = ("TypedDictMonitoringDashboard",)
