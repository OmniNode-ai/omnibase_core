"""
Types for metadata node collection operations.

Provides strongly typed models for validation results and analytics reports.
"""

from datetime import datetime
from typing import Union

from pydantic import BaseModel, ConfigDict, Field


class ModelNodeValidationResult(BaseModel):
    """Result of validating a single node."""

    model_config = ConfigDict(extra="forbid")

    valid: bool = Field(
        ...,
        description="Whether the node is valid",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Validation errors",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Validation warnings",
    )


class ModelCollectionValidationResult(BaseModel):
    """Result of validating an entire collection."""

    model_config = ConfigDict(extra="forbid")

    valid: bool = Field(
        ...,
        description="Whether the entire collection is valid",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Collection-level errors",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Collection-level warnings",
    )
    node_validations: dict[str, ModelNodeValidationResult] = Field(
        default_factory=dict,
        description="Per-node validation results",
    )


class ModelCollectionMetadata(BaseModel):
    """Metadata for a node collection."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        ...,
        description="Collection unique identifier",
    )
    node_count: int = Field(
        ...,
        description="Number of nodes in collection",
        ge=0,
    )
    health_score: float = Field(
        ...,
        description="Collection health score (0-100)",
        ge=0.0,
        le=100.0,
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Report generation timestamp",
    )


class ModelPerformanceMetrics(BaseModel):
    """Performance metrics for a collection."""

    model_config = ConfigDict(extra="forbid")

    total_invocations: int = Field(
        default=0,
        description="Total node invocations across collection",
        ge=0,
    )
    avg_popularity_score: float = Field(
        default=0.0,
        description="Average popularity score",
        ge=0.0,
        le=100.0,
    )
    documentation_coverage: float = Field(
        default=0.0,
        description="Documentation coverage percentage",
        ge=0.0,
        le=100.0,
    )


class ModelNodeBreakdown(BaseModel):
    """Breakdown of nodes by various categories."""

    model_config = ConfigDict(extra="forbid")

    by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Node count by type",
    )
    by_status: dict[str, int] = Field(
        default_factory=dict,
        description="Node count by status",
    )
    by_complexity: dict[str, int] = Field(
        default_factory=dict,
        description="Node count by complexity",
    )


class ModelAnalyticsReport(BaseModel):
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
    performance_metrics: ModelPerformanceMetrics = Field(
        default_factory=ModelPerformanceMetrics,
        description="Performance metrics",
    )
    node_breakdown: ModelNodeBreakdown = Field(
        default_factory=ModelNodeBreakdown,
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
