"""
TypedDict for analytics summary data.

Strongly-typed representation for analytics summary serialization.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict

# Import component classes for type hints
from omnibase_core.models.metadata.analytics.model_analytics_error_summary import (
    ModelAnalyticsErrorSummary,
)
from omnibase_core.models.metadata.analytics.model_analytics_performance_summary import (
    ModelAnalyticsPerformanceSummary,
)
from omnibase_core.types.typed_dict_core_analytics import TypedDictCoreAnalytics
from omnibase_core.types.typed_dict_timestamp_data import TypedDictTimestampData


class TypedDictAnalyticsSummaryData(TypedDict):
    """Strongly-typed structure for analytics summary serialization."""

    core: TypedDictCoreAnalytics
    quality: list[str]  # From component method call - returns list[str]
    errors: ModelAnalyticsErrorSummary  # From component method call
    performance: ModelAnalyticsPerformanceSummary  # From component method call
    timestamps: TypedDictTimestampData


__all__ = ["TypedDictAnalyticsSummaryData"]
