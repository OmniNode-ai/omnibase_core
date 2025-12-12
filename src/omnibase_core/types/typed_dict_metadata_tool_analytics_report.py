"""
TypedDict for complete metadata tool analytics report.

Strongly-typed representation for the complete analytics report for a metadata tool collection.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict

from .typed_dict_collection_metadata import TypedDictCollectionMetadata
from .typed_dict_collection_validation import TypedDictCollectionValidation
from .typed_dict_metadata_tool_analytics_summary_data import (
    TypedDictMetadataToolAnalyticsSummaryData,
)
from .typed_dict_performance_metrics_report import TypedDictPerformanceMetricsReport
from .typed_dict_tool_breakdown import TypedDictToolBreakdown


class TypedDictMetadataToolAnalyticsReport(TypedDict):
    """Complete analytics report for a metadata tool collection."""

    collection_metadata: TypedDictCollectionMetadata
    analytics_summary: TypedDictMetadataToolAnalyticsSummaryData
    performance_metrics: TypedDictPerformanceMetricsReport
    tool_breakdown: TypedDictToolBreakdown
    popular_tools: list[tuple[str, float]]
    validation_results: TypedDictCollectionValidation


__all__ = ["TypedDictMetadataToolAnalyticsReport"]
