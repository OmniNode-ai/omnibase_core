# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for RendererReportJson (OMN-13704).

Covers the JSON report renderer, which generates TypedDictDecisionReport
dictionaries and JSON strings from evidence summaries.

Test Coverage:
- render() top-level key presence (include_details=False)
- render() with include_details=True and non-empty comparisons adds 'details' key
- render() with cost_stats=None leaves performance.cost as None
- render() with cost_stats populated writes all cost sub-fields
- render() raises ValueError for timezone-naive generated_at
- serialize() returns valid JSON string parseable by json.loads()
- Fixed generated_at timestamp appears in output deterministically
- details list correctly serialises comparison fields

Thread Safety:
    All fixtures create immutable models (frozen=True), making them
    thread-safe for use with pytest-xdist parallel execution.
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.evidence.model_cost_statistics import ModelCostStatistics
from omnibase_core.models.evidence.model_decision_recommendation import (
    ModelDecisionRecommendation,
)
from omnibase_core.models.evidence.model_evidence_summary import ModelEvidenceSummary
from omnibase_core.models.evidence.model_invariant_violation_breakdown import (
    ModelInvariantViolationBreakdown,
)
from omnibase_core.models.evidence.model_latency_statistics import (
    ModelLatencyStatistics,
)
from omnibase_core.models.invariant.model_invariant_result import ModelInvariantResult
from omnibase_core.models.replay.model_execution_comparison import (
    ModelExecutionComparison,
)
from omnibase_core.models.replay.model_invariant_comparison_summary import (
    ModelInvariantComparisonSummary,
)
from omnibase_core.rendering.renderer_report_json import (
    REPORT_VERSION,
    RendererReportJson,
)

pytestmark = pytest.mark.unit


# =============================================================================
# Helper Functions (mirrored from test_renderer_report_html.py)
# =============================================================================


def create_latency_stats(
    baseline_avg_ms: float = 100.0,
    replay_avg_ms: float = 100.0,
    baseline_p50_ms: float = 95.0,
    replay_p50_ms: float = 95.0,
    baseline_p95_ms: float = 150.0,
    replay_p95_ms: float = 150.0,
) -> ModelLatencyStatistics:
    """Create latency statistics with computed deltas."""
    delta_avg_ms = replay_avg_ms - baseline_avg_ms
    delta_avg_percent = (
        ((replay_avg_ms - baseline_avg_ms) / baseline_avg_ms * 100.0)
        if baseline_avg_ms != 0
        else 0.0
    )
    delta_p50_percent = (
        ((replay_p50_ms - baseline_p50_ms) / baseline_p50_ms * 100.0)
        if baseline_p50_ms != 0
        else 0.0
    )
    delta_p95_percent = (
        ((replay_p95_ms - baseline_p95_ms) / baseline_p95_ms * 100.0)
        if baseline_p95_ms != 0
        else 0.0
    )
    return ModelLatencyStatistics(
        baseline_avg_ms=baseline_avg_ms,
        baseline_p50_ms=baseline_p50_ms,
        baseline_p95_ms=baseline_p95_ms,
        replay_avg_ms=replay_avg_ms,
        replay_p50_ms=replay_p50_ms,
        replay_p95_ms=replay_p95_ms,
        delta_avg_ms=delta_avg_ms,
        delta_avg_percent=delta_avg_percent,
        delta_p50_percent=delta_p50_percent,
        delta_p95_percent=delta_p95_percent,
    )


def create_cost_stats(
    baseline_total: float = 10.0,
    replay_total: float = 10.0,
    execution_count: int = 10,
) -> ModelCostStatistics:
    """Create cost statistics with computed deltas."""
    delta_total = replay_total - baseline_total
    delta_percent = (
        (delta_total / baseline_total * 100.0) if baseline_total != 0 else 0.0
    )
    baseline_avg = baseline_total / execution_count if execution_count != 0 else 0.0
    replay_avg = replay_total / execution_count if execution_count != 0 else 0.0
    return ModelCostStatistics(
        baseline_total=baseline_total,
        replay_total=replay_total,
        delta_total=delta_total,
        delta_percent=delta_percent,
        baseline_avg_per_execution=baseline_avg,
        replay_avg_per_execution=replay_avg,
    )


def create_violation_breakdown(
    total_violations: int = 0,
    by_type: dict[str, int] | None = None,
    by_severity: dict[str, int] | None = None,
    new_violations: int = 0,
    new_critical_violations: int = 0,
    fixed_violations: int = 0,
) -> ModelInvariantViolationBreakdown:
    """Create an invariant violation breakdown."""
    return ModelInvariantViolationBreakdown(
        total_violations=total_violations,
        by_type=by_type or {},
        by_severity=by_severity or {},
        new_violations=new_violations,
        new_critical_violations=new_critical_violations,
        fixed_violations=fixed_violations,
    )


def create_evidence_summary(
    corpus_id: str = "test-corpus-001",
    baseline_version: str = "v1.0.0",
    replay_version: str = "v1.1.0",
    total_executions: int = 50,
    passed_count: int = 47,
    failed_count: int = 3,
    pass_rate: float = 0.94,
    confidence_score: float = 0.90,
    recommendation: str = "review",
    latency_stats: ModelLatencyStatistics | None = None,
    cost_stats: ModelCostStatistics | None = None,
    invariant_violations: ModelInvariantViolationBreakdown | None = None,
) -> ModelEvidenceSummary:
    """Create an evidence summary for testing."""
    now = datetime.now(tz=UTC)
    return ModelEvidenceSummary(
        corpus_id=corpus_id,
        baseline_version=baseline_version,
        replay_version=replay_version,
        total_executions=total_executions,
        passed_count=passed_count,
        failed_count=failed_count,
        pass_rate=pass_rate,
        confidence_score=confidence_score,
        recommendation=recommendation,  # type: ignore[arg-type]
        latency_stats=latency_stats or create_latency_stats(),
        cost_stats=cost_stats,
        invariant_violations=invariant_violations or create_violation_breakdown(),
        started_at=now - timedelta(hours=1),
        ended_at=now,
    )


def create_invariant_result(
    passed: bool = True,
    severity: EnumSeverity = EnumSeverity.INFO,
    invariant_name: str = "test_invariant",
) -> ModelInvariantResult:
    """Create an invariant result for testing."""
    return ModelInvariantResult(
        invariant_id=uuid4(),
        invariant_name=invariant_name,
        passed=passed,
        severity=severity,
        actual_value="test_actual",
        expected_value="test_expected",
        message="Test invariant result",
    )


def create_execution_comparison(
    output_match: bool = True,
    baseline_passed: bool = True,
    replay_passed: bool = True,
    baseline_latency_ms: float = 100.0,
    replay_latency_ms: float = 105.0,
    baseline_cost: float | None = 0.01,
    replay_cost: float | None = 0.011,
) -> ModelExecutionComparison:
    """Create an execution comparison for testing."""
    baseline_id = uuid4()
    replay_id = uuid4()
    hash_value = "abc123"
    replay_hash = "abc123" if output_match else "def456"

    latency_delta_ms = replay_latency_ms - baseline_latency_ms
    latency_delta_percent = (
        (latency_delta_ms / baseline_latency_ms * 100.0)
        if baseline_latency_ms != 0
        else 0.0
    )

    cost_delta = None
    cost_delta_percent = None
    if baseline_cost is not None and replay_cost is not None:
        cost_delta = replay_cost - baseline_cost
        cost_delta_percent = (
            (cost_delta / baseline_cost * 100.0) if baseline_cost != 0 else 0.0
        )

    baseline_results = [create_invariant_result(passed=baseline_passed)]
    replay_results = [create_invariant_result(passed=replay_passed)]

    comparison_summary = ModelInvariantComparisonSummary(
        total_invariants=1,
        both_passed=1 if (baseline_passed and replay_passed) else 0,
        both_failed=1 if (not baseline_passed and not replay_passed) else 0,
        new_violations=1 if (baseline_passed and not replay_passed) else 0,
        fixed_violations=1 if (not baseline_passed and replay_passed) else 0,
    )

    return ModelExecutionComparison(
        baseline_execution_id=baseline_id,
        replay_execution_id=replay_id,
        input_hash="input_hash_123",
        input_hash_match=True,
        baseline_output_hash=hash_value,
        replay_output_hash=replay_hash,
        output_match=output_match,
        baseline_invariant_results=baseline_results,
        replay_invariant_results=replay_results,
        invariant_comparison=comparison_summary,
        baseline_latency_ms=baseline_latency_ms,
        replay_latency_ms=replay_latency_ms,
        latency_delta_ms=latency_delta_ms,
        latency_delta_percent=latency_delta_percent,
        baseline_cost=baseline_cost,
        replay_cost=replay_cost,
        cost_delta=cost_delta,
        cost_delta_percent=cost_delta_percent,
    )


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_summary() -> ModelEvidenceSummary:
    """Evidence summary with cost stats, latency, and violations."""
    return create_evidence_summary(
        total_executions=50,
        passed_count=47,
        failed_count=3,
        pass_rate=0.94,
        confidence_score=0.90,
        recommendation="review",
        invariant_violations=create_violation_breakdown(
            total_violations=3,
            by_type={"output_equivalence": 2, "latency": 1},
            by_severity={"warning": 2, "critical": 1},
            new_violations=2,
            new_critical_violations=0,
            fixed_violations=1,
        ),
        latency_stats=create_latency_stats(
            baseline_avg_ms=100.0,
            replay_avg_ms=82.0,
        ),
        cost_stats=create_cost_stats(
            baseline_total=10.0,
            replay_total=5.8,
        ),
    )


@pytest.fixture
def sample_recommendation() -> ModelDecisionRecommendation:
    """Recommendation with approve action."""
    return ModelDecisionRecommendation(
        action="approve",
        confidence=0.95,
        blockers=[],
        warnings=["Minor latency increase"],
        next_steps=["Review summary", "Merge PR"],
        rationale="High confidence with no blockers.",
    )


@pytest.fixture
def sample_comparisons() -> list[ModelExecutionComparison]:
    """List of mixed pass/fail execution comparisons."""
    comparisons = []
    for i in range(3):
        comparisons.append(
            create_execution_comparison(
                output_match=True,
                baseline_latency_ms=100.0 + i * 5,
                replay_latency_ms=85.0 + i * 5,
            )
        )
    comparisons.append(
        create_execution_comparison(
            output_match=False,
            baseline_passed=True,
            replay_passed=False,
            baseline_latency_ms=110.0,
            replay_latency_ms=130.0,
        )
    )
    return comparisons


@pytest.fixture
def fixed_timestamp() -> datetime:
    """A fixed UTC timestamp for deterministic output assertions."""
    return datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)


# =============================================================================
# Tests: Top-level Keys
# =============================================================================


class TestRendererReportJsonTopLevelKeys:
    """render() output contains the required top-level keys."""

    def test_render_produces_required_top_level_keys(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
        fixed_timestamp: datetime,
    ) -> None:
        """render() without include_details produces the six mandatory keys."""
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=sample_comparisons,
            recommendation=sample_recommendation,
            include_details=False,
            generated_at=fixed_timestamp,
        )
        assert "report_version" in report
        assert "generated_at" in report
        assert "summary" in report
        assert "violations" in report
        assert "performance" in report
        assert "recommendation" in report

    def test_render_no_details_key_when_false(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
        fixed_timestamp: datetime,
    ) -> None:
        """render() with include_details=False must not include 'details' key."""
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=sample_comparisons,
            recommendation=sample_recommendation,
            include_details=False,
            generated_at=fixed_timestamp,
        )
        assert "details" not in report

    def test_render_report_version_constant(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """report_version should match the module-level REPORT_VERSION constant."""
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=[],
            recommendation=sample_recommendation,
            generated_at=fixed_timestamp,
        )
        assert report["report_version"] == REPORT_VERSION

    def test_render_fixed_timestamp_in_output(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """A fixed generated_at must appear verbatim in the output ISO string."""
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=[],
            recommendation=sample_recommendation,
            generated_at=fixed_timestamp,
        )
        assert report["generated_at"] == fixed_timestamp.isoformat()


# =============================================================================
# Tests: Details Section
# =============================================================================


class TestRendererReportJsonDetails:
    """render() correctly handles the optional 'details' key."""

    def test_render_details_key_present_when_true_and_nonempty(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
        fixed_timestamp: datetime,
    ) -> None:
        """include_details=True with non-empty comparisons must add 'details' key."""
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=sample_comparisons,
            recommendation=sample_recommendation,
            include_details=True,
            generated_at=fixed_timestamp,
        )
        assert "details" in report
        assert isinstance(report["details"], list)
        assert len(report["details"]) == len(sample_comparisons)

    def test_render_details_absent_when_comparisons_empty(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """include_details=True with empty comparisons must NOT add 'details' key."""
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=[],
            recommendation=sample_recommendation,
            include_details=True,
            generated_at=fixed_timestamp,
        )
        assert "details" not in report

    def test_render_details_item_contains_expected_fields(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """Each details item must contain all expected fields."""
        comparison = create_execution_comparison(
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=110.0,
            baseline_cost=0.05,
            replay_cost=0.06,
        )
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=[comparison],
            recommendation=sample_recommendation,
            include_details=True,
            generated_at=fixed_timestamp,
        )
        detail = report["details"][0]  # type: ignore[index]
        assert "comparison_id" in detail
        assert "baseline_execution_id" in detail
        assert "replay_execution_id" in detail
        assert "input_hash" in detail
        assert "input_hash_match" in detail
        assert "output_match" in detail
        assert "baseline_latency_ms" in detail
        assert "replay_latency_ms" in detail
        assert "latency_delta_ms" in detail
        assert "latency_delta_percent" in detail
        assert "baseline_cost" in detail
        assert "replay_cost" in detail
        assert "cost_delta" in detail
        assert "cost_delta_percent" in detail
        assert "compared_at" in detail

    def test_render_details_output_match_values_correct(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """output_match field in detail must reflect the comparison's value."""
        matching = create_execution_comparison(output_match=True)
        failing = create_execution_comparison(output_match=False)
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=[matching, failing],
            recommendation=sample_recommendation,
            include_details=True,
            generated_at=fixed_timestamp,
        )
        details = report["details"]  # type: ignore[misc]
        assert details[0]["output_match"] is True
        assert details[1]["output_match"] is False


# =============================================================================
# Tests: Cost Statistics
# =============================================================================


class TestRendererReportJsonCostStats:
    """render() correctly populates performance.cost."""

    def test_render_cost_none_when_no_cost_stats(
        self,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """performance.cost must be None when summary.cost_stats is None."""
        summary = create_evidence_summary(cost_stats=None)
        report = RendererReportJson.render(
            summary=summary,
            comparisons=[],
            recommendation=sample_recommendation,
            generated_at=fixed_timestamp,
        )
        assert report["performance"]["cost"] is None

    def test_render_cost_populated_when_cost_stats_present(
        self,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """performance.cost must contain all six sub-fields when cost_stats provided."""
        stats = create_cost_stats(
            baseline_total=20.0,
            replay_total=15.0,
            execution_count=5,
        )
        summary = create_evidence_summary(cost_stats=stats)
        report = RendererReportJson.render(
            summary=summary,
            comparisons=[],
            recommendation=sample_recommendation,
            generated_at=fixed_timestamp,
        )
        cost = report["performance"]["cost"]
        assert cost is not None
        assert "baseline_total" in cost
        assert "replay_total" in cost
        assert "delta_total" in cost
        assert "delta_percent" in cost
        assert "baseline_avg_per_execution" in cost
        assert "replay_avg_per_execution" in cost

    def test_render_cost_values_match_stats(
        self,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """performance.cost values must exactly match the source cost_stats."""
        stats = create_cost_stats(
            baseline_total=20.0,
            replay_total=15.0,
            execution_count=5,
        )
        summary = create_evidence_summary(cost_stats=stats)
        report = RendererReportJson.render(
            summary=summary,
            comparisons=[],
            recommendation=sample_recommendation,
            generated_at=fixed_timestamp,
        )
        cost = report["performance"]["cost"]
        assert cost is not None
        assert cost["baseline_total"] == stats.baseline_total
        assert cost["replay_total"] == stats.replay_total
        assert cost["delta_total"] == stats.delta_total
        assert cost["delta_percent"] == stats.delta_percent
        assert cost["baseline_avg_per_execution"] == stats.baseline_avg_per_execution
        assert cost["replay_avg_per_execution"] == stats.replay_avg_per_execution


# =============================================================================
# Tests: Timezone Validation
# =============================================================================


class TestRendererReportJsonTimezoneValidation:
    """render() rejects timezone-naive generated_at."""

    def test_render_raises_for_naive_datetime(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
    ) -> None:
        """Timezone-naive generated_at must raise ValueError."""
        naive_dt = datetime(2025, 1, 15, 10, 30, 0)  # No tzinfo
        with pytest.raises(ValueError, match="timezone-aware"):
            RendererReportJson.render(
                summary=sample_summary,
                comparisons=[],
                recommendation=sample_recommendation,
                generated_at=naive_dt,
            )

    def test_render_accepts_timezone_aware_datetime(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
    ) -> None:
        """Timezone-aware generated_at must not raise."""
        aware_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=[],
            recommendation=sample_recommendation,
            generated_at=aware_dt,
        )
        assert report["generated_at"] == aware_dt.isoformat()

    def test_render_none_generated_at_uses_current_utc(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
    ) -> None:
        """generated_at=None must produce a valid ISO timestamp string."""
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=[],
            recommendation=sample_recommendation,
            generated_at=None,
        )
        generated_at = datetime.fromisoformat(report["generated_at"])
        assert generated_at.tzinfo is not None
        assert generated_at.utcoffset() == timedelta(0)


# =============================================================================
# Tests: serialize()
# =============================================================================


class TestRendererReportJsonSerialize:
    """serialize() returns valid JSON strings."""

    def test_serialize_returns_string(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """serialize() must return a str instance."""
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=[],
            recommendation=sample_recommendation,
            generated_at=fixed_timestamp,
        )
        result = RendererReportJson.serialize(report)
        assert isinstance(result, str)

    def test_serialize_parseable_by_json_loads(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """serialize() output must be parseable by json.loads() without error."""
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=[],
            recommendation=sample_recommendation,
            generated_at=fixed_timestamp,
        )
        json_str = RendererReportJson.serialize(report)
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_serialize_round_trip_preserves_top_level_keys(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """After serialize + json.loads, the top-level keys are still present."""
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=[],
            recommendation=sample_recommendation,
            generated_at=fixed_timestamp,
        )
        parsed = json.loads(RendererReportJson.serialize(report))
        assert "report_version" in parsed
        assert "generated_at" in parsed
        assert "summary" in parsed
        assert "violations" in parsed
        assert "performance" in parsed
        assert "recommendation" in parsed

    def test_serialize_with_details_round_trip(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
        fixed_timestamp: datetime,
    ) -> None:
        """serialize() output with details must round-trip through json.loads."""
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=sample_comparisons,
            recommendation=sample_recommendation,
            include_details=True,
            generated_at=fixed_timestamp,
        )
        parsed = json.loads(RendererReportJson.serialize(report))
        assert "details" in parsed
        assert len(parsed["details"]) == len(sample_comparisons)

    def test_serialize_uses_indentation(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """serialize() must produce indented JSON (not a single-line blob)."""
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=[],
            recommendation=sample_recommendation,
            generated_at=fixed_timestamp,
        )
        json_str = RendererReportJson.serialize(report)
        # Indented JSON contains newlines
        assert "\n" in json_str


# =============================================================================
# Tests: Summary Section Values
# =============================================================================


class TestRendererReportJsonSummaryValues:
    """render() correctly populates the 'summary' sub-dict."""

    def test_render_summary_values_match_input(
        self,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """summary sub-dict values must match the ModelEvidenceSummary fields."""
        summary = create_evidence_summary(
            corpus_id="my-corpus",
            baseline_version="v2.0.0",
            replay_version="v2.1.0",
            total_executions=100,
            passed_count=95,
            failed_count=5,
            pass_rate=0.95,
            confidence_score=0.88,
        )
        report = RendererReportJson.render(
            summary=summary,
            comparisons=[],
            recommendation=sample_recommendation,
            generated_at=fixed_timestamp,
        )
        s = report["summary"]
        assert s["corpus_id"] == "my-corpus"
        assert s["baseline_version"] == "v2.0.0"
        assert s["replay_version"] == "v2.1.0"
        assert s["total_executions"] == 100
        assert s["passed_count"] == 95
        assert s["failed_count"] == 5
        assert s["pass_rate"] == 0.95
        assert s["confidence_score"] == 0.88

    def test_render_summary_started_and_ended_are_iso_strings(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        fixed_timestamp: datetime,
    ) -> None:
        """started_at and ended_at in summary must match source datetimes."""
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=[],
            recommendation=sample_recommendation,
            generated_at=fixed_timestamp,
        )
        assert report["summary"]["started_at"] == sample_summary.started_at.isoformat()
        assert report["summary"]["ended_at"] == sample_summary.ended_at.isoformat()


# =============================================================================
# Tests: Recommendation Section Values
# =============================================================================


class TestRendererReportJsonRecommendationValues:
    """render() correctly populates the 'recommendation' sub-dict."""

    def test_render_recommendation_values_match_input(
        self,
        sample_summary: ModelEvidenceSummary,
        fixed_timestamp: datetime,
    ) -> None:
        """recommendation sub-dict must mirror the ModelDecisionRecommendation fields."""
        rec = ModelDecisionRecommendation(
            action="reject",
            confidence=0.40,
            blockers=["Critical failure"],
            warnings=["High latency"],
            next_steps=["Rollback immediately"],
            rationale="Data corruption detected.",
        )
        report = RendererReportJson.render(
            summary=sample_summary,
            comparisons=[],
            recommendation=rec,
            generated_at=fixed_timestamp,
        )
        r = report["recommendation"]
        assert r["action"] == "reject"
        assert r["confidence"] == 0.40
        assert r["blockers"] == ["Critical failure"]
        assert r["warnings"] == ["High latency"]
        assert r["next_steps"] == ["Rollback immediately"]
        assert r["rationale"] == "Data corruption detected."
