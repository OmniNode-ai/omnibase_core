"""
Metadata Node Analytics Model.

Analytics and metrics for metadata node collections with
performance tracking and health monitoring.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from ..infrastructure.model_metrics_data import ModelMetricsData
from .model_metadata_analytics_summary import ModelMetadataAnalyticsSummary


class ModelMetadataNodeAnalytics(BaseModel):
    """
    Analytics and metrics for metadata node collections.

    Tracks collection performance, health, and usage statistics
    for metadata node collections with proper typing.
    """

    # Collection identification
    collection_name: str = Field(default="", description="Collection name")
    collection_purpose: str = Field(default="general", description="Collection purpose")
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

    # Node categorization
    nodes_by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Node count by type",
    )
    nodes_by_status: dict[str, int] = Field(
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
        default_factory=ModelMetricsData,
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

    def get_node_count_by_type(self, node_type: str) -> int:
        """Get node count for specific type."""
        return self.nodes_by_type.get(node_type, 0)

    def get_node_count_by_status(self, status: str) -> int:
        """Get node count for specific status."""
        return self.nodes_by_status.get(status, 0)

    def get_node_count_by_complexity(self, complexity: str) -> int:
        """Get node count for specific complexity."""
        return self.nodes_by_complexity.get(complexity, 0)

    def get_active_node_count(self) -> int:
        """Get count of active nodes."""
        return self.get_node_count_by_status("active")

    def get_deprecated_node_count(self) -> int:
        """Get count of deprecated nodes."""
        return self.get_node_count_by_status("deprecated")

    def get_disabled_node_count(self) -> int:
        """Get count of disabled nodes."""
        return self.get_node_count_by_status("disabled")

    def get_error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.total_invocations == 0:
            return 0.0
        return (self.error_count / self.total_invocations) * 100.0

    def add_custom_metric(self, name: str, value: Any) -> None:
        """Add a custom metric."""
        self.custom_metrics[name] = value

    def get_custom_metric(self, name: str, default: Any = None) -> Any:
        """Get a custom metric value."""
        return self.custom_metrics.get(name, default)

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
            collection_name=self.collection_name,
            total_nodes=self.total_nodes,
            health_score=self.health_score,
            success_rate=self.overall_success_rate,
            documentation_coverage=self.documentation_coverage,
            active_nodes=self.get_active_node_count(),
            deprecated_nodes=self.get_deprecated_node_count(),
            disabled_nodes=self.get_disabled_node_count(),
            error_count=self.error_count,
            warning_count=self.warning_count,
            last_modified=self.last_modified,
            average_execution_time_ms=self.average_execution_time_ms,
            peak_memory_usage_mb=self.peak_memory_usage_mb,
            total_invocations=self.total_invocations,
            critical_error_count=self.critical_error_count,
        )

    @classmethod
    def create_default(cls, collection_name: str = "") -> "ModelMetadataNodeAnalytics":
        """Create default analytics instance."""
        return cls(
            collection_name=collection_name,
            collection_purpose="general",
        )

    @classmethod
    def create_documentation_analytics(
        cls,
        collection_name: str = "documentation",
    ) -> "ModelMetadataNodeAnalytics":
        """Create analytics optimized for documentation collections."""
        return cls(
            collection_name=collection_name,
            collection_purpose="documentation",
            documentation_coverage=0.0,
        )


# Export for use
__all__ = ["ModelMetadataNodeAnalytics"]
