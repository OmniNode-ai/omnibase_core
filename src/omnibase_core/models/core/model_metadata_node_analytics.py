"""
Metadata node analytics model.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelMetadataNodeAnalytics(BaseModel):
    """Analytics and insights for metadata node collections."""

    collection_created: datetime = Field(
        default_factory=datetime.now,
        description="Collection creation time",
    )
    last_modified: datetime = Field(
        default_factory=datetime.now,
        description="Last modification time",
    )
    total_nodes: int = Field(0, description="Total number of nodes in collection")
    nodes_by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Count of nodes by type",
    )
    nodes_by_status: dict[str, int] = Field(
        default_factory=dict,
        description="Count of nodes by status",
    )
    nodes_by_complexity: dict[str, int] = Field(
        default_factory=dict,
        description="Count of nodes by complexity",
    )

    # Performance analytics
    total_invocations: int = Field(0, description="Total invocations across all nodes")
    overall_success_rate: float = Field(
        100.0,
        description="Overall success rate percentage",
    )
    avg_collection_performance: float = Field(
        0.0,
        description="Average performance across all nodes",
    )

    # Health and quality metrics
    health_score: float = Field(
        100.0,
        description="Overall collection health score (0-100)",
    )
    documentation_coverage: float = Field(
        0.0,
        description="Documentation coverage percentage",
    )
    validation_compliance: float = Field(
        100.0,
        description="Validation compliance percentage",
    )
