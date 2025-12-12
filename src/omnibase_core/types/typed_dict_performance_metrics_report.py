"""
TypedDict for performance metrics report.

Strongly-typed representation for performance metrics in analytics reports.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict


class TypedDictPerformanceMetricsReport(TypedDict):
    """Performance metrics in the analytics report."""

    total_invocations: int
    avg_popularity_score: float
    documentation_coverage: float


__all__ = ["TypedDictPerformanceMetricsReport"]
