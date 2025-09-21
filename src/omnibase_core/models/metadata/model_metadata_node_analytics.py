"""
Metadata Node Analytics Model.

Analytics and metrics for metadata node collections with
performance tracking and health monitoring.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_collection_purpose import EnumCollectionPurpose
from ...enums.enum_metadata_node_status import EnumMetadataNodeStatus
from ...enums.enum_metadata_node_type import EnumMetadataNodeType
from ...utils.uuid_utilities import uuid_from_string
from ..infrastructure.model_metrics_data import ModelMetricsData
from .model_metadata_analytics_summary import ModelMetadataAnalyticsSummary

# Removed Any import - replaced with specific types


class ModelMetadataNodeAnalytics(BaseModel):
    """
    Analytics and metrics for metadata node collections.

    Tracks collection performance, health, and usage statistics
    for metadata node collections with proper typing.
    """

    # Collection identification - UUID-based entity references
    collection_id: UUID = Field(
        default_factory=lambda: uuid_from_string("default", "collection"),
        description="Unique identifier for the collection",
    )
    collection_display_name: str = Field(
        default="", description="Human-readable collection name"
    )
    collection_purpose: EnumCollectionPurpose = Field(
        default=EnumCollectionPurpose.GENERAL, description="Collection purpose"
    )
    collection_created: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Collection creation timestamp",
    )

    # Core metrics
    total_nodes: int = Field(default=0, description="Total number of nodes", ge=0)
    last_modified: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Last modification timestamp",
    )

    last_validated: datetime | None = Field(
        default=None,
        description="Last validation timestamp",
    )

    # Node categorization
    nodes_by_type: dict[EnumMetadataNodeType, int] = Field(
        default_factory=dict,
        description="Node count by type",
    )
    nodes_by_status: dict[EnumMetadataNodeStatus, int] = Field(
        default_factory=dict,
        description="Node count by status",
    )
    nodes_by_complexity: dict[str, int] = Field(
        default_factory=dict,
        description="Node count by complexity",
    )

    # Usage and performance metrics
    total_invocations: int = Field(
        default=0,
        description="Total number of node invocations",
        ge=0,
    )
    overall_success_rate: float = Field(
        default=100.0,
        description="Overall success rate percentage",
        ge=0.0,
        le=100.0,
    )

    # Health and quality metrics
    health_score: float = Field(
        default=100.0,
        description="Overall health score",
        ge=0.0,
        le=100.0,
    )
    documentation_coverage: float = Field(
        default=0.0,
        description="Documentation coverage percentage",
        ge=0.0,
        le=100.0,
    )

    # Performance trends
    average_execution_time_ms: float = Field(
        default=0.0,
        description="Average execution time in milliseconds",
        ge=0.0,
    )
    peak_memory_usage_mb: float = Field(
        default=0.0,
        description="Peak memory usage in MB",
        ge=0.0,
    )

    # Error tracking
    error_count: int = Field(default=0, description="Total error count", ge=0)
    warning_count: int = Field(default=0, description="Total warning count", ge=0)
    critical_error_count: int = Field(
        default=0,
        description="Critical error count",
        ge=0,
    )

    # Custom analytics for extensibility
    custom_metrics: ModelMetricsData = Field(
        default_factory=lambda: ModelMetricsData(
            collection_id=None, collection_display_name="custom_analytics"
        ),
        description="Custom analytics metrics with clean typing",
    )

    def get_success_rate(self) -> float:
        """Get overall success rate."""
        return self.overall_success_rate

    def get_health_score(self) -> float:
        """Get overall health score."""
        return self.health_score

    def get_documentation_coverage(self) -> float:
        """Get documentation coverage percentage."""
        return self.documentation_coverage

    def is_healthy(self) -> bool:
        """Check if collection is healthy (health score > 80)."""
        return self.health_score > 80.0

    def has_good_documentation(self) -> bool:
        """Check if collection has good documentation coverage (> 70%)."""
        return self.documentation_coverage > 70.0

    def get_node_count_by_type(self, node_type: EnumMetadataNodeType) -> int:
        """Get node count for specific type."""
        return self.nodes_by_type.get(node_type, 0)

    def get_node_count_by_status(self, status: EnumMetadataNodeStatus) -> int:
        """Get node count for specific status."""
        return self.nodes_by_status.get(status, 0)

    def get_node_count_by_complexity(self, complexity: str) -> int:
        """Get node count for specific complexity."""
        return self.nodes_by_complexity.get(complexity, 0)

    def get_active_node_count(self) -> int:
        """Get count of active nodes."""
        return self.get_node_count_by_status(EnumMetadataNodeStatus.ACTIVE)

    def get_deprecated_node_count(self) -> int:
        """Get count of deprecated nodes."""
        return self.get_node_count_by_status(EnumMetadataNodeStatus.DEPRECATED)

    def get_disabled_node_count(self) -> int:
        """Get count of disabled nodes."""
        return self.get_node_count_by_status(EnumMetadataNodeStatus.DISABLED)

    def get_error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.total_invocations == 0:
            return 0.0
        return (self.error_count / self.total_invocations) * 100.0

    def add_custom_metric(self, name: str, value: str | int | float | bool) -> None:
        """Add a custom metric."""
        self.custom_metrics.add_metric(name, value)

    def get_custom_metric(
        self, name: str, default: str | int | float | bool | None = None
    ) -> str | int | float | bool | None:
        """Get a custom metric value."""
        value = self.custom_metrics.get_metric_by_key(name)
        return value if value is not None else default

    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.last_modified = datetime.now(UTC).isoformat()

    def calculate_health_score(self) -> float:
        """Calculate and update health score based on metrics."""
        if self.total_nodes == 0:
            self.health_score = 100.0
            return self.health_score

        # Base score from success rate
        base_score = self.overall_success_rate

        # Penalty for deprecated/disabled nodes
        deprecated_ratio = self.get_deprecated_node_count() / max(self.total_nodes, 1)
        disabled_ratio = self.get_disabled_node_count() / max(self.total_nodes, 1)
        penalty = (deprecated_ratio + disabled_ratio) * 20  # Up to 20 point penalty

        # Bonus for good documentation coverage
        doc_bonus = self.documentation_coverage * 0.1  # Up to 10 point bonus

        # Error rate penalty
        error_penalty = self.get_error_rate() * 0.5  # Error rate penalty

        self.health_score = max(
            0.0,
            min(100.0, base_score - penalty + doc_bonus - error_penalty),
        )
        return self.health_score

    def to_summary(self) -> ModelMetadataAnalyticsSummary:
        """Get analytics summary with clean typing."""
        return ModelMetadataAnalyticsSummary(
            collection_id=self.collection_id,
            collection_display_name=self.collection_display_name,
            total_nodes=self.total_nodes,
            health_score=self.health_score,
            success_rate=self.overall_success_rate,
            documentation_coverage=self.documentation_coverage,
            active_nodes=self.get_active_node_count(),
            deprecated_nodes=self.get_deprecated_node_count(),
            disabled_nodes=self.get_disabled_node_count(),
            error_count=self.error_count,
            warning_count=self.warning_count,
            last_modified=(
                datetime.fromisoformat(self.last_modified)
                if self.last_modified
                else None
            ),
            last_validated=self.last_validated,
            average_execution_time_ms=self.average_execution_time_ms,
            peak_memory_usage_mb=self.peak_memory_usage_mb,
            total_invocations=self.total_invocations,
            critical_error_count=self.critical_error_count,
        )

    @classmethod
    def create_default(cls, collection_name: str = "") -> ModelMetadataNodeAnalytics:
        """Create default analytics instance."""
        return cls(
            collection_id=uuid_from_string(collection_name or "default", "collection"),
            collection_display_name=collection_name,
            collection_purpose=EnumCollectionPurpose.GENERAL,
        )

    @classmethod
    def create_documentation_analytics(
        cls,
        collection_name: str = "documentation",
    ) -> ModelMetadataNodeAnalytics:
        """Create analytics optimized for documentation collections."""
        return cls(
            collection_id=uuid_from_string(collection_name, "collection"),
            collection_display_name=collection_name,
            collection_purpose=EnumCollectionPurpose.METADATA,
            documentation_coverage=0.0,
        )


# Export for use
__all__ = ["ModelMetadataNodeAnalytics"]
