"""
Model for baseline health report.

Provides a comprehensive snapshot of system health before proposing changes.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.health.model_invariant_status import ModelInvariantStatus
from omnibase_core.models.health.model_performance_metrics import (
    ModelPerformanceMetrics,
)
from omnibase_core.types.typed_dict_system_config import TypedDictSystemConfig


class ModelBaselineHealthReport(BaseModel):
    """Shows system health before proposing changes.

    This model provides a comprehensive snapshot of system health,
    including invariant status, performance metrics, and stability assessment.
    It serves as a baseline for evaluating the impact of proposed changes.

    Attributes:
        report_id: Unique identifier for this report.
        generated_at: Timestamp when the report was generated.
        current_config: Current system configuration.
        config_hash: Hash of the configuration for quick comparison.
        corpus_size: Number of samples in the execution corpus.
        corpus_date_range: Date range of corpus samples.
        input_diversity_score: Score indicating input variety (0-1).
        invariants_checked: List of invariant check results.
        all_invariants_passing: True if all invariants passed.
        metrics: Performance metrics summary.
        stability_score: Overall stability score (0-1).
        stability_status: Categorical stability status.
        stability_details: Detailed explanation of stability assessment.
        confidence_level: Confidence in the assessment (0-1).
        confidence_reasoning: Explanation of confidence level.

    Example:
        >>> from datetime import datetime
        >>> from uuid import uuid4
        >>> metrics = ModelPerformanceMetrics(
        ...     avg_latency_ms=150.5,
        ...     p95_latency_ms=450.0,
        ...     p99_latency_ms=800.0,
        ...     avg_cost_per_call=0.002,
        ...     total_calls=10000,
        ...     error_rate=0.01
        ... )
        >>> report = ModelBaselineHealthReport(
        ...     report_id=uuid4(),
        ...     generated_at=datetime.now(),
        ...     current_config={"model": "gpt-4"},
        ...     config_hash="abc123def456",
        ...     corpus_size=1000,
        ...     corpus_date_range=(datetime(2024, 1, 1), datetime(2024, 1, 31)),
        ...     input_diversity_score=0.85,
        ...     invariants_checked=[],
        ...     all_invariants_passing=True,
        ...     metrics=metrics,
        ...     stability_score=0.92,
        ...     stability_status="stable",
        ...     stability_details="All metrics within normal range",
        ...     confidence_level=0.95,
        ...     confidence_reasoning="Large corpus with diverse inputs"
        ... )
        >>> report.stability_status
        'stable'
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    report_id: UUID = Field(
        ...,
        description="Unique identifier for this report",
    )
    generated_at: datetime = Field(
        ...,
        description="Timestamp when the report was generated",
    )

    # Current Configuration
    current_config: TypedDictSystemConfig = Field(
        ...,
        description="Current system configuration",
    )
    config_hash: str = Field(
        ...,
        description="Hash of the configuration for quick comparison",
    )

    # Corpus Summary
    corpus_size: int = Field(
        ...,
        ge=0,
        description="Number of samples in the execution corpus",
    )
    corpus_date_range: tuple[datetime, datetime] = Field(
        ...,
        description="Date range of corpus samples (start, end)",
    )
    input_diversity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Score indicating input variety (0-1)",
    )

    # Invariant Status
    invariants_checked: list[ModelInvariantStatus] = Field(
        ...,
        description="List of invariant check results",
    )
    all_invariants_passing: bool = Field(
        ...,
        description="True if all invariants passed",
    )

    # Performance Metrics
    metrics: ModelPerformanceMetrics = Field(
        ...,
        description="Performance metrics summary",
    )

    # Stability Assessment
    stability_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall stability score (0-1)",
    )
    stability_status: Literal["stable", "unstable", "degraded"] = Field(
        ...,
        description="Categorical stability status",
    )
    stability_details: str = Field(
        ...,
        description="Detailed explanation of stability assessment",
    )

    # Confidence
    confidence_level: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the assessment (0-1)",
    )
    confidence_reasoning: str = Field(
        ...,
        description="Explanation of confidence level",
    )

    def is_stable(self) -> bool:
        """Check if the system is in a stable state.

        Returns:
            True if stability_status is 'stable' and all invariants are passing.
        """
        return self.stability_status == "stable" and self.all_invariants_passing

    def is_safe_for_changes(self, min_stability_score: float = 0.8) -> bool:
        """Determine if it's safe to propose changes based on baseline health.

        Args:
            min_stability_score: Minimum stability score required (default 0.8).

        Returns:
            True if the system meets minimum stability requirements.
        """
        return (
            self.is_stable()
            and self.stability_score >= min_stability_score
            and self.confidence_level >= 0.7
        )

    def get_failing_invariants(self) -> list[ModelInvariantStatus]:
        """Get list of invariants that failed their checks.

        Returns:
            List of ModelInvariantStatus objects where passed is False.
        """
        return [inv for inv in self.invariants_checked if not inv.passed]
