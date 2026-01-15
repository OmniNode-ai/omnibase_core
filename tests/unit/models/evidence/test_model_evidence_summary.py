# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelEvidenceSummary."""

from datetime import UTC, datetime, timedelta

import pytest

from omnibase_core.errors import ModelOnexError
from omnibase_core.models.evidence import (
    ModelEvidenceSummary,
)


def make_comparison(
    *,
    comparison_id: str = "cmp-001",
    baseline_passed: bool = True,
    replay_passed: bool = True,
    baseline_latency_ms: float = 100.0,
    replay_latency_ms: float = 100.0,
    baseline_cost: float | None = 0.01,
    replay_cost: float | None = 0.01,
    violation_deltas: list[dict] | None = None,
    executed_at: datetime | None = None,
) -> dict:
    """Helper to create comparison dictionaries for testing."""
    return {
        "comparison_id": comparison_id,
        "baseline_passed": baseline_passed,
        "replay_passed": replay_passed,
        "baseline_latency_ms": baseline_latency_ms,
        "replay_latency_ms": replay_latency_ms,
        "baseline_cost": baseline_cost,
        "replay_cost": replay_cost,
        "violation_deltas": violation_deltas or [],
        "executed_at": executed_at or datetime.now(tz=UTC),
    }


@pytest.mark.unit
class TestAggregation:
    """Test aggregation of multiple comparisons."""

    def test_aggregate_empty_comparisons(self) -> None:
        """Handle empty comparison list gracefully - raises ModelOnexError."""
        with pytest.raises(ModelOnexError, match="comparisons list cannot be empty"):
            ModelEvidenceSummary.from_comparisons(
                comparisons=[],
                corpus_id="corpus-001",
                baseline_version="v1.0.0",
                replay_version="v1.1.0",
            )

    def test_aggregate_single_comparison(self) -> None:
        """Correctly summarize single comparison."""
        comparison = make_comparison(
            baseline_passed=True,
            replay_passed=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=90.0,
        )

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=[comparison],
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.total_executions == 1
        assert summary.passed_count == 1
        assert summary.failed_count == 0
        assert summary.pass_rate == 1.0
        assert summary.corpus_id == "corpus-001"
        assert summary.baseline_version == "v1.0.0"
        assert summary.replay_version == "v1.1.0"

    def test_aggregate_multiple_comparisons(self) -> None:
        """Correctly summarize multiple comparisons."""
        comparisons = [
            make_comparison(
                comparison_id=f"cmp-{i}",
                replay_passed=(i % 10 != 0),  # 10% failure rate
            )
            for i in range(1, 51)  # 50 comparisons
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.total_executions == 50
        assert summary.passed_count == 45  # 50 - 5 failed
        assert summary.failed_count == 5

    def test_pass_rate_calculation(self) -> None:
        """Pass rate is passed_count / total_executions."""
        comparisons = [
            make_comparison(comparison_id="cmp-1", replay_passed=True),
            make_comparison(comparison_id="cmp-2", replay_passed=True),
            make_comparison(comparison_id="cmp-3", replay_passed=True),
            make_comparison(comparison_id="cmp-4", replay_passed=False),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.pass_rate == 0.75  # 3/4

    def test_pass_fail_counting(self) -> None:
        """Correctly counts passed and failed executions."""
        comparisons = [
            make_comparison(comparison_id="cmp-1", replay_passed=True),
            make_comparison(comparison_id="cmp-2", replay_passed=False),
            make_comparison(comparison_id="cmp-3", replay_passed=False),
            make_comparison(comparison_id="cmp-4", replay_passed=True),
            make_comparison(comparison_id="cmp-5", replay_passed=True),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.passed_count == 3
        assert summary.failed_count == 2
        assert summary.total_executions == 5


@pytest.mark.unit
class TestStatisticalCalculations:
    """Test statistical calculations."""

    def test_latency_average_calculation(self) -> None:
        """Average latency calculated correctly."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                baseline_latency_ms=100.0,
                replay_latency_ms=80.0,
            ),
            make_comparison(
                comparison_id="cmp-2",
                baseline_latency_ms=200.0,
                replay_latency_ms=160.0,
            ),
            make_comparison(
                comparison_id="cmp-3",
                baseline_latency_ms=150.0,
                replay_latency_ms=120.0,
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        # Baseline: (100 + 200 + 150) / 3 = 150
        assert summary.latency_stats.baseline_avg_ms == 150.0
        # Replay: (80 + 160 + 120) / 3 = 120
        assert summary.latency_stats.replay_avg_ms == 120.0

    def test_latency_p50_calculation(self) -> None:
        """P50 (median) latency calculated correctly."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                baseline_latency_ms=100.0,
                replay_latency_ms=80.0,
            ),
            make_comparison(
                comparison_id="cmp-2",
                baseline_latency_ms=200.0,
                replay_latency_ms=160.0,
            ),
            make_comparison(
                comparison_id="cmp-3",
                baseline_latency_ms=150.0,
                replay_latency_ms=120.0,
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        # Sorted baseline: [100, 150, 200] -> median = 150
        assert summary.latency_stats.baseline_p50_ms == 150.0
        # Sorted replay: [80, 120, 160] -> median = 120
        assert summary.latency_stats.replay_p50_ms == 120.0

    def test_latency_p95_calculation(self) -> None:
        """P95 latency calculated correctly."""
        # Create 20 comparisons for meaningful P95
        comparisons = [
            make_comparison(
                comparison_id=f"cmp-{i}",
                baseline_latency_ms=float(i * 10),  # 10, 20, ..., 200
                replay_latency_ms=float(i * 8),  # 8, 16, ..., 160
            )
            for i in range(1, 21)
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        # P95 should be near the high end
        # For 20 values: ceil(0.95 * 20) - 1 = 19 - 1 = 18 (0-indexed)
        # Sorted baseline: 10, 20, ..., 200 -> index 18 = 190
        assert summary.latency_stats.baseline_p95_ms == 190.0
        # Sorted replay: 8, 16, ..., 160 -> index 18 = 152
        assert summary.latency_stats.replay_p95_ms == 152.0

    def test_latency_delta_percentages(self) -> None:
        """Delta percentages calculated correctly."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                baseline_latency_ms=100.0,
                replay_latency_ms=82.0,  # 18% improvement
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        # Delta = (82 - 100) / 100 * 100 = -18%
        assert summary.latency_stats.delta_avg_percent == pytest.approx(-18.0)

    def test_cost_statistics_with_missing_data(self) -> None:
        """Cost stats are None if any execution missing cost."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                baseline_cost=0.01,
                replay_cost=0.01,
            ),
            make_comparison(
                comparison_id="cmp-2",
                baseline_cost=0.02,
                replay_cost=None,  # Missing cost
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.cost_stats is None

    def test_cost_statistics_calculation(self) -> None:
        """Cost statistics calculated correctly when all present."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                baseline_cost=0.10,
                replay_cost=0.06,
            ),
            make_comparison(
                comparison_id="cmp-2",
                baseline_cost=0.10,
                replay_cost=0.05,
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.cost_stats is not None
        assert summary.cost_stats.baseline_total == pytest.approx(0.20)
        assert summary.cost_stats.replay_total == pytest.approx(0.11)
        # Delta = (0.11 - 0.20) / 0.20 * 100 = -45%
        assert summary.cost_stats.delta_percent == pytest.approx(-45.0)


@pytest.mark.unit
class TestInvariantBreakdown:
    """Test invariant violation breakdown."""

    def test_violation_count_by_type(self) -> None:
        """Correctly groups violations by type."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                violation_deltas=[
                    {
                        "type": "output_equivalence",
                        "severity": "critical",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                    {
                        "type": "latency",
                        "severity": "warning",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                ],
            ),
            make_comparison(
                comparison_id="cmp-2",
                violation_deltas=[
                    {
                        "type": "output_equivalence",
                        "severity": "critical",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                ],
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.invariant_violations.by_type["output_equivalence"] == 2
        assert summary.invariant_violations.by_type["latency"] == 1

    def test_violation_count_by_severity(self) -> None:
        """Correctly groups violations by severity."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                violation_deltas=[
                    {
                        "type": "output_equivalence",
                        "severity": "critical",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                    {
                        "type": "latency",
                        "severity": "warning",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                    {
                        "type": "cost",
                        "severity": "warning",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                ],
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.invariant_violations.by_severity["critical"] == 1
        assert summary.invariant_violations.by_severity["warning"] == 2

    def test_new_vs_fixed_violations(self) -> None:
        """Correctly identifies new and fixed violations."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                violation_deltas=[
                    {
                        "type": "output_equivalence",
                        "severity": "critical",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },  # New violation
                    {
                        "type": "latency",
                        "severity": "warning",
                        "baseline_passed": False,
                        "replay_passed": True,
                    },  # Fixed violation
                    {
                        "type": "cost",
                        "severity": "info",
                        "baseline_passed": False,
                        "replay_passed": False,
                    },  # Existing violation
                ],
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.invariant_violations.new_violations == 1
        assert summary.invariant_violations.fixed_violations == 1

    def test_total_violation_count(self) -> None:
        """Total matches sum of individual violations."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                violation_deltas=[
                    {
                        "type": "output_equivalence",
                        "severity": "critical",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                    {
                        "type": "latency",
                        "severity": "warning",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                ],
            ),
            make_comparison(
                comparison_id="cmp-2",
                violation_deltas=[
                    {
                        "type": "cost",
                        "severity": "info",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                ],
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.invariant_violations.total_violations == 3
        total_by_type = sum(summary.invariant_violations.by_type.values())
        assert summary.invariant_violations.total_violations == total_by_type


@pytest.mark.unit
class TestConfidenceScoring:
    """Test confidence score calculation."""

    def test_perfect_pass_rate_high_confidence(self) -> None:
        """100% pass rate yields high confidence (>=0.95)."""
        comparisons = [
            make_comparison(comparison_id=f"cmp-{i}", replay_passed=True)
            for i in range(10)
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.confidence_score >= 0.95

    def test_low_pass_rate_low_confidence(self) -> None:
        """Low pass rate yields low confidence (<0.7)."""
        # 50% pass rate
        comparisons = [
            make_comparison(comparison_id="cmp-1", replay_passed=True),
            make_comparison(comparison_id="cmp-2", replay_passed=False),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.confidence_score < 0.7

    def test_critical_violations_reduce_confidence(self) -> None:
        """Critical violations significantly reduce confidence."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                replay_passed=True,
                violation_deltas=[
                    {
                        "type": "output_equivalence",
                        "severity": "critical",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                ],
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        # Perfect pass rate but critical violation -> significant penalty
        assert summary.confidence_score < 0.6

    def test_performance_regression_affects_confidence(self) -> None:
        """Large performance regressions (>50%) affect confidence."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                replay_passed=True,
                baseline_latency_ms=100.0,
                replay_latency_ms=200.0,  # 100% regression
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        # 100% pass rate but 100% latency regression -> penalty applied
        assert summary.confidence_score < 1.0
        assert summary.confidence_score >= 0.85  # Penalty is 0.1

    def test_confidence_bounds(self) -> None:
        """Confidence is always between 0.0 and 1.0."""
        # Test with various scenarios
        scenarios = [
            # All passing, no issues
            [make_comparison(comparison_id="cmp-1", replay_passed=True)],
            # All failing
            [make_comparison(comparison_id="cmp-1", replay_passed=False)],
            # Mixed with violations
            [
                make_comparison(
                    comparison_id="cmp-1",
                    replay_passed=False,
                    violation_deltas=[
                        {
                            "type": "output_equivalence",
                            "severity": "critical",
                            "baseline_passed": True,
                            "replay_passed": False,
                        },
                    ],
                ),
            ],
        ]

        for comparisons in scenarios:
            summary = ModelEvidenceSummary.from_comparisons(
                comparisons=comparisons,
                corpus_id="corpus-001",
                baseline_version="v1.0.0",
                replay_version="v1.1.0",
            )

            assert 0.0 <= summary.confidence_score <= 1.0


@pytest.mark.unit
class TestRecommendation:
    """Test recommendation generation."""

    def test_approve_recommendation(self) -> None:
        """High confidence (>=0.95), no critical issues -> approve."""
        comparisons = [
            make_comparison(
                comparison_id=f"cmp-{i}",
                replay_passed=True,
                baseline_latency_ms=100.0,
                replay_latency_ms=90.0,  # Improvement
            )
            for i in range(10)
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.recommendation == "approve"

    def test_review_recommendation(self) -> None:
        """Medium confidence or minor issues -> review."""
        # 90% pass rate -> medium confidence
        comparisons = [
            make_comparison(comparison_id=f"cmp-{i}", replay_passed=(i != 0))
            for i in range(10)
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.recommendation == "review"

    def test_reject_recommendation(self) -> None:
        """Low confidence (<0.70) or critical issues -> reject."""
        # 50% pass rate -> low confidence
        comparisons = [
            make_comparison(comparison_id="cmp-1", replay_passed=True),
            make_comparison(comparison_id="cmp-2", replay_passed=False),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.recommendation == "reject"

    def test_critical_violation_forces_reject(self) -> None:
        """Any new critical violation forces reject regardless of confidence."""
        comparisons = [
            make_comparison(
                comparison_id=f"cmp-{i}",
                replay_passed=True,
                violation_deltas=(
                    [
                        {
                            "type": "output_equivalence",
                            "severity": "critical",
                            "baseline_passed": True,
                            "replay_passed": False,
                        }
                    ]
                    if i == 0
                    else []
                ),
            )
            for i in range(10)
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.recommendation == "reject"


@pytest.mark.unit
class TestHeadline:
    """Test headline generation."""

    def test_headline_format(self) -> None:
        """Headline matches format: '47/50 passed, 3 violations, latency -18%, cost -42%'."""
        comparisons = [
            make_comparison(
                comparison_id=f"cmp-{i}",
                replay_passed=(i <= 47),  # 47 pass, 3 fail
                baseline_latency_ms=100.0,
                replay_latency_ms=82.0,  # -18% latency
                baseline_cost=0.10,
                replay_cost=0.058,  # -42% cost
                violation_deltas=(
                    [
                        {
                            "type": "output",
                            "severity": "warning",
                            "baseline_passed": True,
                            "replay_passed": False,
                        }
                    ]
                    if i > 47
                    else []
                ),
            )
            for i in range(1, 51)  # 50 comparisons
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        headline = summary.headline
        assert "47/50 passed" in headline
        assert "3 violations" in headline
        assert "latency" in headline.lower()
        assert "-18%" in headline
        assert "cost" in headline.lower()
        assert "-42%" in headline

    def test_headline_without_cost(self) -> None:
        """Headline omits cost when cost_stats is None."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                baseline_cost=0.01,
                replay_cost=None,  # Missing cost
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        headline = summary.headline
        assert "passed" in headline
        assert "cost" not in headline.lower()


@pytest.mark.unit
class TestCriticalViolationsIdentification:
    """Test correct identification of NEW critical violations.

    These tests verify the fix for correctly identifying violations that are
    in current (replay) but NOT in baseline. A "new critical violation" is:
    - baseline_passed=True (was passing in baseline)
    - replay_passed=False (now failing in replay)
    - severity="critical"

    This is distinct from:
    - Existing violations (failed in both)
    - Fixed violations (failed in baseline, passed in replay)
    - Non-critical new violations (new but warning/info severity)
    """

    def test_identifies_new_critical_not_existing(self) -> None:
        """NEW critical violations are correctly identified vs existing ones."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                replay_passed=True,
                violation_deltas=[
                    # NEW critical: was passing, now failing
                    {
                        "type": "output_equivalence",
                        "severity": "critical",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                    # EXISTING critical: was failing, still failing (NOT new)
                    {
                        "type": "data_integrity",
                        "severity": "critical",
                        "baseline_passed": False,
                        "replay_passed": False,
                    },
                ],
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        # Only 1 is NEW critical (output_equivalence), not data_integrity
        assert summary.invariant_violations.new_critical_violations == 1
        # Both are current violations (failed in replay)
        assert summary.invariant_violations.by_severity["critical"] == 2
        # Only 1 is NEW (the output_equivalence)
        assert summary.invariant_violations.new_violations == 1

    def test_distinguishes_new_critical_from_fixed(self) -> None:
        """NEW critical violations are distinguished from FIXED ones."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                replay_passed=True,
                violation_deltas=[
                    # NEW critical: was passing, now failing (regression)
                    {
                        "type": "schema_validation",
                        "severity": "critical",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                    # FIXED critical: was failing, now passing (improvement)
                    {
                        "type": "security_check",
                        "severity": "critical",
                        "baseline_passed": False,
                        "replay_passed": True,
                    },
                ],
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        # NEW critical: only schema_validation
        assert summary.invariant_violations.new_critical_violations == 1
        # Fixed: security_check was fixed
        assert summary.invariant_violations.fixed_violations == 1
        # Current critical violations: only schema_validation (security_check passed)
        assert summary.invariant_violations.by_severity.get("critical", 0) == 1

    def test_new_critical_vs_new_non_critical(self) -> None:
        """NEW critical are counted separately from NEW non-critical."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                replay_passed=True,
                violation_deltas=[
                    # NEW critical
                    {
                        "type": "output_equivalence",
                        "severity": "critical",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                    # NEW warning (not critical)
                    {
                        "type": "latency",
                        "severity": "warning",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                    # NEW info (not critical)
                    {
                        "type": "cost",
                        "severity": "info",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                ],
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        # Only 1 is NEW + critical
        assert summary.invariant_violations.new_critical_violations == 1
        # All 3 are NEW (passed in baseline, failed in replay)
        assert summary.invariant_violations.new_violations == 3
        # Total violations
        assert summary.invariant_violations.total_violations == 3

    def test_multiple_new_critical_across_comparisons(self) -> None:
        """NEW critical violations are aggregated across multiple comparisons."""
        comparisons = [
            make_comparison(
                comparison_id="cmp-1",
                replay_passed=True,
                violation_deltas=[
                    # NEW critical #1
                    {
                        "type": "output_equivalence",
                        "severity": "critical",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                ],
            ),
            make_comparison(
                comparison_id="cmp-2",
                replay_passed=True,
                violation_deltas=[
                    # NEW critical #2
                    {
                        "type": "schema_validation",
                        "severity": "critical",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                    # EXISTING critical (not new)
                    {
                        "type": "data_integrity",
                        "severity": "critical",
                        "baseline_passed": False,
                        "replay_passed": False,
                    },
                ],
            ),
            make_comparison(
                comparison_id="cmp-3",
                replay_passed=True,
                violation_deltas=[
                    # NEW critical #3
                    {
                        "type": "security",
                        "severity": "critical",
                        "baseline_passed": True,
                        "replay_passed": False,
                    },
                ],
            ),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        # 3 NEW critical violations across all comparisons
        assert summary.invariant_violations.new_critical_violations == 3
        # 4 total critical violations (3 new + 1 existing)
        assert summary.invariant_violations.by_severity["critical"] == 4
        # 3 NEW violations total (all are critical in this case)
        assert summary.invariant_violations.new_violations == 3

    def test_new_critical_triggers_reject_recommendation(self) -> None:
        """Any NEW critical violation should trigger 'reject' recommendation."""
        # Perfect pass rate but with new critical violation
        comparisons = [
            make_comparison(
                comparison_id=f"cmp-{i}",
                replay_passed=True,
                baseline_latency_ms=100.0,
                replay_latency_ms=90.0,  # Good latency
                violation_deltas=(
                    [
                        {
                            "type": "output_equivalence",
                            "severity": "critical",
                            "baseline_passed": True,  # NEW
                            "replay_passed": False,
                        }
                    ]
                    if i == 0
                    else []
                ),
            )
            for i in range(10)
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        # Despite 100% pass rate and good latency, should reject due to new critical
        assert summary.pass_rate == 1.0
        assert summary.invariant_violations.new_critical_violations == 1
        assert summary.recommendation == "reject"

    def test_existing_critical_does_not_trigger_reject_alone(self) -> None:
        """EXISTING critical violations (not new) don't force reject by themselves."""
        comparisons = [
            make_comparison(
                comparison_id=f"cmp-{i}",
                replay_passed=True,
                violation_deltas=[
                    {
                        "type": "known_issue",
                        "severity": "critical",
                        "baseline_passed": False,  # EXISTING - was already failing
                        "replay_passed": False,
                    },
                ],
            )
            for i in range(10)
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        # No NEW critical violations
        assert summary.invariant_violations.new_critical_violations == 0
        # But there ARE existing critical violations
        assert summary.invariant_violations.by_severity["critical"] == 10
        # High pass rate + no new criticals = could be approve
        # (assuming confidence >= 0.95)
        assert summary.pass_rate == 1.0
        assert summary.recommendation == "approve"


@pytest.mark.unit
class TestModelProperties:
    """Test model configuration and properties."""

    def test_model_is_frozen(self) -> None:
        """Model is immutable after creation."""
        comparisons = [make_comparison(comparison_id="cmp-1")]
        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        with pytest.raises(Exception):  # ValidationError for frozen models
            summary.total_executions = 999  # type: ignore[misc]

    def test_summary_id_is_generated(self) -> None:
        """Each summary gets a unique ID."""
        comparisons = [make_comparison(comparison_id="cmp-1")]

        summary1 = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        summary2 = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary1.summary_id != summary2.summary_id

    def test_timestamps_are_set(self) -> None:
        """Started/ended timestamps are captured from comparisons."""
        now = datetime.now(tz=UTC)
        earlier = now - timedelta(hours=1)

        comparisons = [
            make_comparison(comparison_id="cmp-1", executed_at=earlier),
            make_comparison(comparison_id="cmp-2", executed_at=now),
        ]

        summary = ModelEvidenceSummary.from_comparisons(
            comparisons=comparisons,
            corpus_id="corpus-001",
            baseline_version="v1.0.0",
            replay_version="v1.1.0",
        )

        assert summary.started_at == earlier
        assert summary.ended_at == now
        assert summary.generated_at >= now
