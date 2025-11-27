from pydantic import Field

"""
Metadata tool analytics model.
"""

from datetime import datetime

from pydantic import BaseModel


class ModelMetadataToolAnalytics(BaseModel):
    """Analytics and insights for metadata tool collections."""

    collection_created: datetime = Field(
        default_factory=datetime.now,
        description="Collection creation time",
    )
    last_modified: datetime = Field(
        default_factory=datetime.now,
        description="Last modification time",
    )
    total_tools: int = Field(
        default=0, description="Total number of tools in collection"
    )
    tools_by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Count of tools by type",
    )
    tools_by_status: dict[str, int] = Field(
        default_factory=dict,
        description="Count of tools by status",
    )
    tools_by_complexity: dict[str, int] = Field(
        default_factory=dict,
        description="Count of tools by complexity",
    )

    # Performance analytics
    total_invocations: int = Field(
        default=0, description="Total invocations across all tools"
    )
    overall_success_rate: float = Field(
        default=100.0,
        description="Overall success rate percentage",
    )
    avg_collection_performance: float = Field(
        default=0.0,
        description="Average performance across all tools",
    )

    # Health and quality metrics
    health_score: float = Field(
        default=100.0,
        description="Overall collection health score (0-100)",
    )
    documentation_coverage: float = Field(
        default=0.0,
        description="Documentation coverage percentage",
    )
    validation_compliance: float = Field(
        default=100.0,
        description="Validation compliance percentage",
    )
