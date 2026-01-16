"""Evidence summary model for corpus replay aggregation.

This model aggregates all comparisons from a corpus replay into a decision-ready
summary with confidence scoring and recommendations (OMN-1195).

Thread Safety:
    ModelEvidenceSummary is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field

from omnibase_core.enums import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError
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
    ) -> "ModelEvidenceSummary":
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
                - executed_at: datetime (optional; if missing or not datetime,
                  uses current UTC time for started_at/ended_at)
            corpus_id: The corpus that was replayed.
            baseline_version: Version of the baseline execution.
            replay_version: Version being tested.

        Returns:
            ModelEvidenceSummary with aggregated metrics.

        Raises:
            ModelOnexError: If comparisons list is empty.

        Note:
            **Timestamp handling**: If no valid executed_at timestamps are found
            in comparisons, both started_at and ended_at will default to the
            current UTC time.

            **Cost statistics (cost_stats) - graceful degradation**: The cost_stats
            field will be None when cost data is incomplete. This occurs when:

            - ANY comparison has baseline_cost=None (missing baseline cost)
            - ANY comparison has replay_cost=None (missing replay cost)
            - ANY comparison has non-numeric cost values (converted to None)

            This is intentional graceful degradation, not an error. Cost tracking
            is optional in corpus replay, and incomplete cost data should not
            prevent summary generation. When cost_stats is None:

            - The headline omits the cost delta (shows "47/50 passed, 3 violations,
              latency -18%" instead of including ", cost -42%")
            - Confidence scoring skips the cost penalty factor
            - All other metrics (pass rate, violations, latency) remain functional

            See ModelCostStatistics.from_cost_values() for the underlying logic.
        """
        if not comparisons:
            raise ModelOnexError(
                message="comparisons list cannot be empty",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"field": "comparisons", "reason": "empty_list"},
            )

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
            # Fallback: use current time if no executed_at timestamps provided.
            # This handles comparisons created without explicit timestamps.
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

        Output Range:
            Always returns a value in [0.0, 1.0], clamped at both ends.

        Formula:
            confidence = 1.0
            confidence *= pass_rate  # Primary factor (multiplicative)
            if invariant_violations.new_critical_violations > 0:
                confidence *= 0.5  # Heavy penalty for NEW critical violations
            if latency_stats.delta_avg_percent > 50:
                confidence -= 0.1  # Secondary penalty (subtractive)
            if cost_stats is not None and cost_stats.delta_percent > 50:
                confidence -= 0.05  # Secondary penalty (subtractive)
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]

        Design Rationale (Intentional Two-Tier Penalty System):
            This formula uses INTENTIONALLY different penalty mechanisms:

            1. MULTIPLICATIVE (pass_rate): The pass_rate multiplication is the
               PRIMARY quality signal. It scales confidence proportionally - if
               only 80% of tests pass, confidence can never exceed 0.8 regardless
               of other factors. This ensures pass_rate dominates the score.

            2. SUBTRACTIVE (latency/cost): These are SECONDARY adjustments that
               apply fixed penalties when thresholds are exceeded. They represent
               "additional concerns" that warrant caution even when tests pass.

            This is NOT a "double penalty" but rather a hierarchical system:
            - Pass rate determines the ceiling (multiplicative)
            - Performance regressions lower the floor (subtractive)

            The design ensures that a 100% pass rate with severe latency regression
            still yields a lower confidence than 100% pass rate with acceptable
            performance, while maintaining pass_rate as the dominant factor.

        NEW critical violations are regressions: invariants that passed in baseline
        but failed in replay (baseline_passed=True, replay_passed=False, severity=critical).

        Example Calculations:
            Example 1 - Perfect score:
                pass_rate=1.0, no violations, latency_delta=10%, no cost data
                confidence = 1.0 * 1.0 = 1.0 (no penalties apply)
                Result: 1.0

            Example 2 - Moderate pass rate only:
                pass_rate=0.8, no violations, latency_delta=20%, no cost data
                confidence = 1.0 * 0.8 = 0.8 (no penalties apply)
                Result: 0.8

            Example 3 - Good pass rate with latency regression:
                pass_rate=0.95, no violations, latency_delta=60%, no cost data
                confidence = 1.0 * 0.95 = 0.95
                confidence = 0.95 - 0.1 = 0.85 (latency penalty)
                Result: 0.85

            Example 4 - Perfect pass rate with both regressions:
                pass_rate=1.0, no violations, latency_delta=60%, cost_delta=60%
                confidence = 1.0 * 1.0 = 1.0
                confidence = 1.0 - 0.1 = 0.9 (latency penalty)
                confidence = 0.9 - 0.05 = 0.85 (cost penalty)
                Result: 0.85

            Example 5 - New critical violation:
                pass_rate=0.9, new_critical=1, latency_delta=10%, no cost data
                confidence = 1.0 * 0.9 = 0.9
                confidence = 0.9 * 0.5 = 0.45 (critical violation penalty)
                Result: 0.45

            Example 6 - Worst case (all penalties):
                pass_rate=0.7, new_critical=1, latency_delta=60%, cost_delta=60%
                confidence = 1.0 * 0.7 = 0.7
                confidence = 0.7 * 0.5 = 0.35 (critical violation)
                confidence = 0.35 - 0.1 = 0.25 (latency)
                confidence = 0.25 - 0.05 = 0.2 (cost)
                Result: 0.2

        Args:
            pass_rate: Ratio of passed executions (0.0 - 1.0).
            invariant_violations: Violation breakdown including new/fixed counts.
            latency_stats: Latency statistics with delta percentages.
            cost_stats: Cost statistics (may be None if incomplete data).

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        confidence = 1.0

        # Primary factor: pass rate
        confidence *= pass_rate

        # Heavy penalty for new critical violations
        # (baseline_passed=True, replay_passed=False, severity=critical)
        if invariant_violations.new_critical_violations > 0:
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
            - "approve": confidence >= 0.95, no NEW critical violations
            - "reject": confidence < 0.70 OR any NEW critical violation (regression)
            - "review": everything else

        NEW critical violations are regressions: invariants that passed in baseline
        but failed in replay (baseline_passed=True, replay_passed=False, severity=critical).

        Args:
            confidence: Calculated confidence score.
            invariant_violations: Violation breakdown including new/fixed counts.

        Returns:
            Recommendation: "approve", "review", or "reject".
        """
        # Any new critical violation forces reject
        if invariant_violations.new_critical_violations > 0:
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
