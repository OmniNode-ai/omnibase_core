"""
Comprehensive analytics report for a node collection.

Aggregates all collection data including metadata, performance metrics,
node breakdowns, and validation results into a unified report.
"""

from typing import Union

from pydantic import BaseModel, ConfigDict, Field

from .model_collection_metadata import ModelCollectionMetadata
from .model_collection_node_breakdown import ModelCollectionNodeBreakdown
from .model_collection_performance_metrics import ModelCollectionPerformanceMetrics
from .model_collection_validation_result import ModelCollectionValidationResult


class ModelCollectionAnalyticsReport(BaseModel):
    """Comprehensive analytics report for a collection."""

    model_config = ConfigDict(extra="forbid")

    collection_metadata: ModelCollectionMetadata = Field(
        ...,
        description="Collection metadata",
    )
    analytics_summary: dict[str, Union[str, int, float]] = Field(
        default_factory=dict,
        description="Analytics summary data",
    )
    performance_metrics: ModelCollectionPerformanceMetrics = Field(
        default_factory=ModelCollectionPerformanceMetrics,
        description="Performance metrics",
    )
    node_breakdown: ModelCollectionNodeBreakdown = Field(
        default_factory=ModelCollectionNodeBreakdown,
        description="Node breakdown by categories",
    )
    popular_nodes: list[tuple[str, float]] = Field(
        default_factory=list,
        description="Popular nodes with scores",
    )
    validation_results: ModelCollectionValidationResult = Field(
        ...,
        description="Collection validation results",
    )
