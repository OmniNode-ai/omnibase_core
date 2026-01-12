"""
Model for baseline health report.

Provides a comprehensive snapshot of system health before proposing changes.

Timezone Handling:
    All datetime fields in this model accept both naive and timezone-aware
    datetime objects. For consistency across distributed systems, it is
    **strongly recommended** to use timezone-aware UTC datetimes:

    .. code-block:: python

        from datetime import UTC, datetime

        report = ModelBaselineHealthReport(
            generated_at=datetime.now(UTC),
            corpus_date_range=(datetime(2024, 1, 1, tzinfo=UTC),
                               datetime(2024, 1, 31, tzinfo=UTC)),
            ...
        )

    Using UTC ensures:

    - Consistent ordering when comparing reports across time zones
    - Correct duration calculations for corpus_date_range
    - Unambiguous timestamps in logs and audit trails

Example Workflow::

    from datetime import UTC, datetime
    from uuid import uuid4
    from omnibase_core.utils.util_stability_calculator import (
        calculate_stability,
        calculate_confidence,
    )

    # 1. Calculate metrics
    stability_score, status, details = calculate_stability(
        invariants, metrics, corpus_size
    )
    confidence, reasoning = calculate_confidence(
        corpus_size, diversity, inv_count
    )

    # 2. Create report
    report = ModelBaselineHealthReport(
        report_id=uuid4(),
        generated_at=datetime.now(UTC),
        stability_score=stability_score,
        stability_status=status,
        confidence_level=confidence,
        # ... other fields
    )

    # 3. Use report
    if report.is_safe_for_changes():
        propose_optimization()
"""

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.health.model_invariant_status import ModelInvariantStatus
from omnibase_core.models.health.model_performance_metrics import (
    ModelPerformanceMetrics,
)
from omnibase_core.types.typed_dict_system_config import TypedDictSystemConfig

MAX_CORPUS_SIZE = 1_000_000_000
"""Maximum allowed corpus size (1 billion samples).

Rationale: This upper bound prevents memory exhaustion when processing
corpus statistics. In practice, corpora rarely exceed millions of samples,
and 1 billion provides a generous safety margin while preventing
unreasonable values that could indicate data corruption or input errors.
"""


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
        >>> from datetime import UTC, datetime
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
        ...     generated_at=datetime.now(UTC),
        ...     current_config={"model": "gpt-4"},
        ...     config_hash="abc123def456",
        ...     corpus_size=1000,
        ...     corpus_date_range=(
        ...         datetime(2024, 1, 1, tzinfo=UTC),
        ...         datetime(2024, 1, 31, tzinfo=UTC),
        ...     ),
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

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    report_id: UUID = Field(
        ...,
        description="Unique identifier for this report",
    )
    generated_at: datetime = Field(
        ...,
        description=(
            "Timestamp when the report was generated. "
            "Recommend using UTC timezone (datetime.now(UTC)) for consistency."
        ),
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
        le=MAX_CORPUS_SIZE,
        description="Number of samples in the execution corpus",
    )
    corpus_date_range: tuple[datetime, datetime] = Field(
        ...,
        description=(
            "Date range of corpus samples (start, end). "
            "Recommend using UTC timezone for consistency in duration calculations."
        ),
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

    @model_validator(mode="after")
    def _validate_date_range_ordering(self) -> Self:
        """Validate that corpus_date_range start is before or equal to end.

        Returns:
            Self: The validated model instance.

        Raises:
            ModelOnexError: If start date is after end date.
        """
        start, end = self.corpus_date_range
        if start > end:
            raise ModelOnexError(
                message=(
                    f"corpus_date_range start must be before or equal to end "
                    f"(start={start.isoformat()}, end={end.isoformat()})"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                start=start.isoformat(),
                end=end.isoformat(),
            )
        return self

    def is_stable(self) -> bool:
        """Check if the system is in a stable state.

        Returns:
            True if stability_status is 'stable' and all invariants are passing.
        """
        return self.stability_status == "stable" and self.all_invariants_passing

    def is_safe_for_changes(
        self,
        min_stability_score: float = 0.8,
        min_confidence: float = 0.7,
    ) -> bool:
        """Check if system is safe for making changes.

        Args:
            min_stability_score: Minimum required stability score (default: 0.8).
            min_confidence: Minimum required confidence level (default: 0.7).

        Returns:
            True if system is stable with sufficient confidence for changes.
        """
        return (
            self.is_stable()
            and self.stability_score >= min_stability_score
            and self.confidence_level >= min_confidence
        )

    def get_failing_invariants(self) -> list[ModelInvariantStatus]:
        """Get list of invariants that failed their checks.

        Returns:
            List of ModelInvariantStatus objects where passed is False.
        """
        return [inv for inv in self.invariants_checked if not inv.passed]

    def __str__(self) -> str:
        """Return a human-readable summary of the health report.

        Returns:
            String representation with report ID, status, score, and confidence.
        """
        return (
            f"Health Report {self.report_id}: "
            f"{self.stability_status} (score={self.stability_score:.2f}, "
            f"confidence={self.confidence_level:.2f})"
        )
