"""
Convert legacy stats dict[str, Any] to TypedDict.
"""

from __future__ import annotations

from .typed_dict_execution_stats import TypedDictExecutionStats
from .typed_dict_legacy_stats import TypedDictLegacyStats


def convert_stats_to_typed_dict(stats: TypedDictLegacyStats) -> TypedDictExecutionStats:
    """Convert legacy stats dict[str, Any] to TypedDict."""
    # Lazy import to avoid circular import:
    # types -> utils -> models.errors -> types
    from omnibase_core.utils.util_datetime_parser import parse_datetime

    return TypedDictExecutionStats(
        execution_count=int(stats.get("execution_count", 0) or 0),
        success_count=int(stats.get("success_count", 0) or 0),
        failure_count=int(stats.get("failure_count", 0) or 0),
        average_duration_ms=float(stats.get("average_duration_ms", 0.0) or 0.0),
        last_execution=parse_datetime(stats.get("last_execution")),
        total_duration_ms=int(stats.get("total_duration_ms", 0) or 0),
    )
