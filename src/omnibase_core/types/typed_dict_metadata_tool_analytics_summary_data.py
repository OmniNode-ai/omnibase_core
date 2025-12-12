"""
TypedDict for metadata tool analytics summary data.

Strongly-typed representation for summary data from ModelMetadataToolAnalytics.model_dump().
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict


class TypedDictMetadataToolAnalyticsSummaryData(TypedDict):
    """Summary data from ModelMetadataToolAnalytics.model_dump()."""

    collection_created: str
    last_modified: str
    total_tools: int
    tools_by_type: dict[str, int]
    tools_by_status: dict[str, int]
    tools_by_complexity: dict[str, int]
    total_invocations: int
    overall_success_rate: float
    avg_collection_performance: float
    health_score: float
    documentation_coverage: float
    validation_compliance: float


__all__ = ["TypedDictMetadataToolAnalyticsSummaryData"]
