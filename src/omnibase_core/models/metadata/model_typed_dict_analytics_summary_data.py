from __future__ import annotations

from typing import Dict, TypedDict

"""
Typed structure for analytics summary serialization.
"""


from typing import TypedDict

# Import component classes for type hints
from omnibase_core.models.analytics.model_analytics_error_summary import (
    ModelAnalyticsErrorSummary,
)
from omnibase_core.models.analytics.model_analytics_performance_summary import (
    ModelAnalyticsPerformanceSummary,
)
from omnibase_core.models.metadata.model_typed_dict_core_analytics import (
    ModelTypedDictCoreAnalytics,
)
from omnibase_core.models.metadata.model_typed_dict_timestamp_data import (
    ModelTypedDictTimestampData,
)


class TypedDictAnalyticsSummaryData(TypedDict):
    """Typed structure for analytics summary serialization."""

    core: ModelTypedDictCoreAnalytics
    quality: list[str]  # From component method call - returns list[str]
    errors: ModelAnalyticsErrorSummary  # From component method call - returns ModelAnalyticsErrorSummary
    performance: ModelAnalyticsPerformanceSummary  # From component method call - returns ModelAnalyticsPerformanceSummary
    timestamps: ModelTypedDictTimestampData


__all__ = ["ModelTypedDictAnalyticsSummaryData"]
