# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Evidence summary model for corpus replay aggregation.

This model aggregates all comparisons from a corpus replay into a decision-ready
summary with confidence scoring and recommendations (OMN-1195).

Thread Safety:
    ModelEvidenceSummary is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field

from omnibase_core.models.evidence.model_cost_statistics import ModelCostStatistics
from omnibase_core.models.evidence.model_invariant_violation_breakdown import (
    ModelInvariantViolationBreakdown,
)
from omnibase_core.models.evidence.model_latency_statistics import (
    ModelLatencyStatistics,
)


class ModelEvidenceSummary(BaseModel):
    """Aggregated evidence from corpus replay for decision-making.

    This is the main "headline" model that aggregates all comparisons from
    a corpus replay into a decision-ready summary with confidence scoring.

    Attributes:
        summary_id: Unique identifier for this summary.
        corpus_id: The corpus that was replayed.
        baseline_version: Version of the baseline execution.
        replay_version: Version being tested.
        total_executions: Total number of comparisons processed.
        passed_count: Number of comparisons where replay passed.
        failed_count: Number of comparisons where replay failed.
        pass_rate: Ratio of passed to total (0.0 - 1.0).
        invariant_violations: Breakdown of violations by type/severity.
        latency_stats: Latency comparison statistics.
        cost_stats: Cost comparison statistics (None if incomplete data).
        confidence_score: Overall confidence in the replay (0.0 - 1.0).
        recommendation: Suggested action (approve/review/reject).
        generated_at: When this summary was generated.
        started_at: Timestamp of earliest comparison.
        ended_at: Timestamp of latest comparison.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # Identification
    summary_id: str = Field(  # string-id-ok: generated UUID as string for serialization
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this summary",
    )
    corpus_id: str = Field(  # string-id-ok: external corpus identifier
        description="The corpus that was replayed"
    )
    baseline_version: str = Field(  # string-version-ok: external version identifier
        description="Version of the baseline execution"
    )
    replay_version: str = Field(  # string-version-ok: external version identifier
        description="Version being tested"
    )

    # Execution Counts
    total_executions: int = Field(
        ge=0, description="Total number of comparisons processed"
    )
    passed_count: int = Field(
        ge=0, description="Number of comparisons where replay passed"
    )
    failed_count: int = Field(
        ge=0, description="Number of comparisons where replay failed"
    )
    pass_rate: float = Field(
        ge=0.0, le=1.0, description="Ratio of passed to total (0.0 - 1.0)"
    )

    # Invariant Breakdown
    invariant_violations: ModelInvariantViolationBreakdown = Field(
        description="Breakdown of violations by type and severity"
    )

    # Performance Statistics
    latency_stats: ModelLatencyStatistics = Field(
        description="Latency comparison statistics"
    )

    # Cost Statistics (optional - None if incomplete data)
    cost_stats: ModelCostStatistics | None = Field(
        default=None, description="Cost comparison statistics (None if incomplete data)"
    )

    # Overall Assessment
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Overall confidence in the replay (0.0 - 1.0)"
    )
    recommendation: Literal["approve", "review", "reject"] = Field(
        description="Suggested action based on confidence and violations"
    )

    # Metadata
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="When this summary was generated",
    )
    started_at: datetime = Field(description="Timestamp of earliest comparison")
    ended_at: datetime = Field(description="Timestamp of latest comparison")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def headline(self) -> str:
        """Generate headline summary.

        Format: '47/50 passed, 3 violations, latency -18%, cost -42%'

        Returns:
            Human-readable headline string.
        """
        parts = [f"{self.passed_count}/{self.total_executions} passed"]
        parts.append(
            f"{self.invariant_violations.total_violations} violation"
            f"{'s' if self.invariant_violations.total_violations != 1 else ''}"
        )

        # Format latency delta
        latency_delta = self.latency_stats.delta_avg_percent
        latency_sign = "+" if latency_delta > 0 else ""
        parts.append(f"latency {latency_sign}{latency_delta:.0f}%")

        # Add cost if available
        if self.cost_stats is not None:
            cost_delta = self.cost_stats.delta_percent
            cost_sign = "+" if cost_delta > 0 else ""
            parts.append(f"cost {cost_sign}{cost_delta:.0f}%")

        return ", ".join(parts)

    @classmethod
    def from_comparisons(
        cls,
        comparisons: list[dict[str, object]],
        corpus_id: str,  # string-id-ok: external corpus identifier
        baseline_version: str,  # string-version-ok: external version identifier
        replay_version: str,  # string-version-ok: external version identifier
    ) -> ModelEvidenceSummary:
        """Aggregate comparisons into an evidence summary.

        Args:
            comparisons: List of comparison dictionaries with structure:
                - comparison_id: str
                - baseline_passed: bool
                - replay_passed: bool
                - baseline_latency_ms: float
                - replay_latency_ms: float
                - baseline_cost: float | None
                - replay_cost: float | None
                - violation_deltas: list[dict]
                - executed_at: datetime
            corpus_id: The corpus that was replayed.
            baseline_version: Version of the baseline execution.
            replay_version: Version being tested.

        Returns:
            ModelEvidenceSummary with aggregated metrics.

        Raises:
            ValueError: If comparisons list is empty.
        """
        if not comparisons:
            # error-ok: factory method validation, simpler than OnexError for caller
            raise ValueError("comparisons cannot be empty")

        # Calculate pass/fail counts
        total = len(comparisons)
        passed = sum(1 for c in comparisons if c.get("replay_passed", False))
        failed = total - passed
        pass_rate = passed / total

        # Aggregate violation deltas
        all_violation_deltas: list[dict[str, object]] = []
        for comparison in comparisons:
            violation_deltas = comparison.get("violation_deltas", [])
            if isinstance(violation_deltas, list):
                for vd in violation_deltas:
                    if isinstance(vd, dict):
                        all_violation_deltas.append(vd)

        invariant_violations = ModelInvariantViolationBreakdown.from_violation_deltas(
            all_violation_deltas
        )

        # Calculate latency statistics
        baseline_latencies: list[float] = []
        replay_latencies: list[float] = []
        for c in comparisons:
            bl = c.get("baseline_latency_ms", 0.0)
            rl = c.get("replay_latency_ms", 0.0)
            baseline_latencies.append(
                float(bl) if isinstance(bl, (int, float)) else 0.0
            )
            replay_latencies.append(float(rl) if isinstance(rl, (int, float)) else 0.0)

        latency_stats = ModelLatencyStatistics.from_latency_values(
            baseline_values=baseline_latencies,
            replay_values=replay_latencies,
        )

        # Calculate cost statistics (may be None)
        baseline_costs: list[float | None] = []
        replay_costs: list[float | None] = []
        for c in comparisons:
            bc = c.get("baseline_cost")
            rc = c.get("replay_cost")
            baseline_costs.append(float(bc) if isinstance(bc, (int, float)) else None)
            replay_costs.append(float(rc) if isinstance(rc, (int, float)) else None)

        cost_stats = ModelCostStatistics.from_cost_values(
            baseline_costs=baseline_costs,
            replay_costs=replay_costs,
        )

        # Determine timestamps
        executed_times: list[datetime] = []
        for c in comparisons:
            et = c.get("executed_at")
            if isinstance(et, datetime):
                executed_times.append(et)

        if executed_times:
            started_at = min(executed_times)
            ended_at = max(executed_times)
        else:
            now = datetime.now(tz=UTC)
            started_at = now
            ended_at = now

        # Calculate confidence score
        confidence = cls._calculate_confidence(
            pass_rate=pass_rate,
            invariant_violations=invariant_violations,
            latency_stats=latency_stats,
            cost_stats=cost_stats,
        )

        # Determine recommendation
        recommendation = cls._determine_recommendation(
            confidence=confidence,
            invariant_violations=invariant_violations,
        )

        return cls(
            corpus_id=corpus_id,
            baseline_version=baseline_version,
            replay_version=replay_version,
            total_executions=total,
            passed_count=passed,
            failed_count=failed,
            pass_rate=pass_rate,
            invariant_violations=invariant_violations,
            latency_stats=latency_stats,
            cost_stats=cost_stats,
            confidence_score=confidence,
            recommendation=recommendation,
            started_at=started_at,
            ended_at=ended_at,
        )

    @classmethod
    def _calculate_confidence(
        cls,
        pass_rate: float,
        invariant_violations: ModelInvariantViolationBreakdown,
        latency_stats: ModelLatencyStatistics,
        cost_stats: ModelCostStatistics | None,
    ) -> float:
        """Calculate confidence score using weighted factors.

        Formula:
            confidence = 1.0
            confidence *= pass_rate  # Primary factor
            if new_critical_violations > 0:
                confidence *= 0.5  # Heavy penalty for critical violations
            if delta_latency_percent > 50:
                confidence -= 0.1  # Moderate penalty for 50%+ regression
            if delta_cost_percent > 50:
                confidence -= 0.05  # Minor penalty for cost increase
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]

        Args:
            pass_rate: Ratio of passed executions (0.0 - 1.0).
            invariant_violations: Violation breakdown.
            latency_stats: Latency statistics.
            cost_stats: Cost statistics (may be None).

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        confidence = 1.0

        # Primary factor: pass rate
        confidence *= pass_rate

        # Heavy penalty for new critical violations
        # Check for new critical violations (baseline_passed=True, replay_passed=False, severity=critical)
        new_critical_count = invariant_violations.by_severity.get("critical", 0)
        # Only count as "new critical" if there are actually new violations
        # and they are in the critical severity bucket
        if new_critical_count > 0 and invariant_violations.new_violations > 0:
            confidence *= 0.5

        # Moderate penalty for significant latency regression (>50%)
        if latency_stats.delta_avg_percent > 50:
            confidence -= 0.1

        # Minor penalty for significant cost increase (>50%)
        if cost_stats is not None and cost_stats.delta_percent > 50:
            confidence -= 0.05

        # Clamp to [0, 1]
        return max(0.0, min(1.0, confidence))

    @classmethod
    def _determine_recommendation(
        cls,
        confidence: float,
        invariant_violations: ModelInvariantViolationBreakdown,
    ) -> Literal["approve", "review", "reject"]:
        """Determine recommendation based on confidence and violations.

        Thresholds:
            - "approve": confidence >= 0.95, no new critical violations
            - "reject": confidence < 0.70 OR any new critical violation
            - "review": everything else

        Args:
            confidence: Calculated confidence score.
            invariant_violations: Violation breakdown.

        Returns:
            Recommendation: "approve", "review", or "reject".
        """
        # Check for new critical violations
        has_new_critical = (
            invariant_violations.by_severity.get("critical", 0) > 0
            and invariant_violations.new_violations > 0
        )

        # Any new critical violation forces reject
        if has_new_critical:
            return "reject"

        # Low confidence -> reject
        if confidence < 0.70:
            return "reject"

        # High confidence and no critical issues -> approve
        if confidence >= 0.95:
            return "approve"

        # Everything else -> review
        return "review"


__all__ = ["ModelEvidenceSummary"]
