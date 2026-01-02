"""
ModelHealthStatus - Rich health status model for comprehensive health tracking

This model replaces restrictive health enums with extensible health management
supporting subsystem health, issues tracking, metrics, and trend analysis.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from .model_health_issue import ModelHealthIssue
from .model_health_metadata import ModelHealthMetadata
from .model_health_metric import ModelHealthMetric


class ModelHealthStatus(BaseModel):
    """
    Rich health status model for comprehensive health tracking

    This model provides multi-dimensional health status tracking including:
    - Overall and subsystem health status
    - Health score calculation with configurable thresholds
    - Issue tracking with severity and categorization
    - Metrics collection and trend analysis
    - Health check performance tracking
    - Auto-healing and maintenance mode support
    """

    status: str = Field(
        default=...,
        description="Primary health status",
        pattern="^(healthy|degraded|unhealthy|unknown|custom)$",
    )

    health_score: float = Field(
        default=...,
        description="Overall health score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    subsystem_health: dict[str, "ModelHealthStatus"] = Field(
        default_factory=dict,
        description="Health status of subsystems",
    )

    metrics: list[ModelHealthMetric] = Field(
        default_factory=list,
        description="Health metrics collection",
    )

    issues: list[ModelHealthIssue] = Field(
        default_factory=list,
        description="Current health issues",
    )

    last_check: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last health check timestamp",
    )

    next_check: datetime | None = Field(
        default=None,
        description="Next scheduled health check",
    )

    check_duration_ms: int | None = Field(
        default=None,
        description="Health check duration in milliseconds",
        ge=0,
    )

    check_count: int = Field(
        default=0,
        description="Total number of health checks performed",
        ge=0,
    )

    uptime_seconds: int | None = Field(
        default=None,
        description="System uptime in seconds",
        ge=0,
    )

    metadata: ModelHealthMetadata | None = Field(
        default=None,
        description="Additional health metadata",
    )

    def is_healthy(self, threshold: float = 0.7) -> bool:
        """
        Check if health meets the specified threshold

        Args:
            threshold: Health score threshold (0.0-1.0)

        Returns:
            True if health score meets or exceeds threshold
        """
        return self.health_score >= threshold

    def is_degraded(self, degraded_threshold: float = 0.5) -> bool:
        """
        Check if health is in degraded state

        Args:
            degraded_threshold: Threshold below which health is considered degraded

        Returns:
            True if health is degraded but not completely unhealthy
        """
        return degraded_threshold <= self.health_score < 0.7

    def is_critical(self) -> bool:
        """
        Check if health status is critical

        Returns:
            True if there are critical issues or very low health score
        """
        return (
            self.health_score < 0.3
            or any(issue.severity == "critical" for issue in self.issues)
            or self.status == "unhealthy"
        )

    def get_critical_issues(self) -> list[ModelHealthIssue]:
        """Get all critical health issues"""
        return [issue for issue in self.issues if issue.severity == "critical"]

    def get_high_issues(self) -> list[ModelHealthIssue]:
        """Get all high severity health issues"""
        return [issue for issue in self.issues if issue.severity == "high"]

    def get_metric_by_name(self, metric_name: str) -> ModelHealthMetric | None:
        """Get a specific health metric by name"""
        for metric in self.metrics:
            if metric.metric_name == metric_name:
                return metric
        return None

    def get_subsystem_health_summary(self) -> dict[str, str]:
        """Get summary of all subsystem health statuses"""
        return {name: health.status for name, health in self.subsystem_health.items()}

    def calculate_overall_health_score(self) -> float:
        """
        Calculate overall health score based on subsystems and issues

        Returns:
            Calculated health score (0.0-1.0)
        """
        if not self.subsystem_health and not self.issues:
            return self.health_score

        # Start with base score
        score = self.health_score

        # Factor in subsystem health
        if self.subsystem_health:
            subsystem_scores = [
                health.health_score for health in self.subsystem_health.values()
            ]
            avg_subsystem_score = sum(subsystem_scores) / len(subsystem_scores)
            score = (score + avg_subsystem_score) / 2

        # Reduce score based on issues
        issue_penalty = 0.0
        for issue in self.issues:
            if issue.severity == "critical":
                issue_penalty += 0.3
            elif issue.severity == "high":
                issue_penalty += 0.1
            elif issue.severity == "medium":
                issue_penalty += 0.05

        score = max(0.0, score - issue_penalty)
        return min(1.0, score)

    def needs_attention(self) -> bool:
        """Check if health status requires immediate attention"""
        return (
            self.is_critical()
            or len(self.get_critical_issues()) > 0
            or len(self.get_high_issues()) > 3
            or self.health_score < 0.5
        )

    def get_health_summary(self) -> str:
        """Get human-readable health summary"""
        critical_count = len(self.get_critical_issues())
        high_count = len(self.get_high_issues())

        if self.is_critical():
            return f"CRITICAL: {critical_count} critical issues, score {self.health_score:.1%}"
        if self.is_degraded():
            return f"DEGRADED: {high_count} high issues, score {self.health_score:.1%}"
        if self.is_healthy():
            return f"HEALTHY: score {self.health_score:.1%}"
        return f"UNKNOWN: score {self.health_score:.1%}"

    @classmethod
    def create_healthy(cls, score: float = 1.0) -> "ModelHealthStatus":
        """Create a healthy status instance"""
        return cls(status="healthy", health_score=score, check_count=1)

    @classmethod
    def create_degraded(
        cls,
        score: float = 0.6,
        issues: list[ModelHealthIssue] | None = None,
    ) -> "ModelHealthStatus":
        """Create a degraded status instance"""
        return cls(
            status="degraded",
            health_score=score,
            issues=issues if issues is not None else [],
            check_count=1,
        )

    @classmethod
    def create_unhealthy(
        cls,
        score: float = 0.2,
        issues: list[ModelHealthIssue] | None = None,
    ) -> "ModelHealthStatus":
        """Create an unhealthy status instance"""
        return cls(
            status="unhealthy",
            health_score=score,
            issues=issues if issues is not None else [],
            check_count=1,
        )


# Enable forward references for recursive subsystem health.
# This rebuild is required for the self-referential subsystem_health field.
# The try/except handles cases where nested models have unresolved forward references
# during circular import resolution - these will be resolved later in __init__.py
try:
    ModelHealthStatus.model_rebuild()
except (
    Exception
):  # error-ok: model_rebuild may fail during import, resolved in __init__.py
    pass
