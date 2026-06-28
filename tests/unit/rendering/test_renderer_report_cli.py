# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for RendererReportCli (OMN-13706).

Covers the main render() path including verbosity branches, violation breakdown,
latency and cost formatting, private helpers, and error handling.

Thread Safety:
    All fixtures create immutable models (frozen=True), making them
    thread-safe for use with pytest-xdist parallel execution.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.errors.model_onex_error import ModelOnexError
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
from omnibase_core.rendering.renderer_report_cli import (
    COMPARISON_LIMIT_CLI_VERBOSE,
    COST_NA_CLI,
    REPORT_WIDTH,
    RendererReportCli,
)

pytestmark = pytest.mark.unit

# =============================================================================
# Helper Functions
# =============================================================================


def create_latency_stats(
    baseline_avg_ms: float = 100.0,
    replay_avg_ms: float = 110.0,
    baseline_p50_ms: float = 95.0,
    replay_p50_ms: float = 100.0,
    baseline_p95_ms: float = 150.0,
    replay_p95_ms: float = 160.0,
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
        replay_avg_ms=replay_avg_ms,
        delta_avg_ms=delta_avg_ms,
        delta_avg_percent=delta_avg_percent,
        baseline_p50_ms=baseline_p50_ms,
        replay_p50_ms=replay_p50_ms,
        delta_p50_percent=delta_p50_percent,
        baseline_p95_ms=baseline_p95_ms,
        replay_p95_ms=replay_p95_ms,
        delta_p95_percent=delta_p95_percent,
    )


def create_cost_stats(
    baseline_total: float = 1.0,
    replay_total: float = 1.1,
    executions: int = 10,
) -> ModelCostStatistics:
    """Create cost statistics with computed deltas."""
    delta_total = replay_total - baseline_total
    delta_percent = (
        ((replay_total - baseline_total) / baseline_total * 100.0)
        if baseline_total != 0
        else 0.0
    )
    return ModelCostStatistics(
        baseline_total=baseline_total,
        replay_total=replay_total,
        delta_total=delta_total,
        delta_percent=delta_percent,
        baseline_avg_per_execution=baseline_total / executions,
        replay_avg_per_execution=replay_total / executions,
    )


def create_violation_breakdown(
    total_violations: int = 0,
    by_type: dict[str, int] | None = None,
    by_severity: dict[str, int] | None = None,
    new_violations: int = 0,
    new_critical_violations: int = 0,
    fixed_violations: int = 0,
) -> ModelInvariantViolationBreakdown:
    """Create violation breakdown for testing."""
    return ModelInvariantViolationBreakdown(
        total_violations=total_violations,
        by_type=by_type or {},
        by_severity=by_severity or {},
        new_violations=new_violations,
        new_critical_violations=new_critical_violations,
        fixed_violations=fixed_violations,
    )


def create_evidence_summary(
    corpus_id: str = "test-corpus",
    baseline_version: str = "1.0.0",
    replay_version: str = "1.1.0",
    total_executions: int = 100,
    passed_count: int = 95,
    failed_count: int = 5,
    pass_rate: float = 0.95,
    confidence_score: float = 0.90,
    recommendation: Literal["approve", "review", "reject"] = "review",
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
        recommendation=recommendation,
        latency_stats=latency_stats or create_latency_stats(),
        cost_stats=cost_stats,
        invariant_violations=invariant_violations or create_violation_breakdown(),
        started_at=now - timedelta(hours=1),
        ended_at=now,
    )


def create_recommendation(
    action: Literal["approve", "review", "reject"] = "approve",
    confidence: float = 0.9,
    rationale: str = "All tests passed with acceptable performance.",
    blockers: list[str] | None = None,
    warnings: list[str] | None = None,
    next_steps: list[str] | None = None,
) -> ModelDecisionRecommendation:
    """Create a recommendation for testing."""
    return ModelDecisionRecommendation(
        action=action,
        confidence=confidence,
        rationale=rationale,
        blockers=blockers or [],
        warnings=warnings or [],
        next_steps=next_steps or [],
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
        baseline_execution_id=uuid4(),
        replay_execution_id=uuid4(),
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
# render() — verbosity='minimal'
# =============================================================================


class TestRenderMinimalVerbosity:
    """render() with verbosity='minimal' delegates to render_minimal."""

    def test_returns_short_string(self) -> None:
        """render() with minimal verbosity returns a 2-line string."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()

        result = RendererReportCli.render(
            summary, [], recommendation, verbosity="minimal"
        )

        lines = result.strip().split("\n")
        # render_minimal produces exactly 2 lines
        assert len(lines) == 2

    def test_does_not_include_separator(self) -> None:
        """render() with minimal verbosity omits the full-width separator."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()

        result = RendererReportCli.render(
            summary, [], recommendation, verbosity="minimal"
        )

        assert "=" * REPORT_WIDTH not in result

    def test_matches_render_minimal_output(self) -> None:
        """render() with minimal verbosity returns same output as render_minimal()."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()

        via_render = RendererReportCli.render(
            summary, [], recommendation, verbosity="minimal"
        )
        direct = RendererReportCli.render_minimal(summary, recommendation)

        assert via_render == direct

    def test_contains_recommendation_action(self) -> None:
        """Minimal output includes the uppercase recommendation action."""
        summary = create_evidence_summary()
        recommendation = create_recommendation(action="reject", confidence=0.4)

        result = RendererReportCli.render(
            summary, [], recommendation, verbosity="minimal"
        )

        assert "REJECT" in result


# =============================================================================
# render() — verbosity='standard'
# =============================================================================


class TestRenderStandardVerbosity:
    """render() with verbosity='standard' includes summary, violations, performance."""

    def test_contains_header_separator(self) -> None:
        """Standard output starts and ends with the full-width separator."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()

        result = RendererReportCli.render(
            summary, [], recommendation, verbosity="standard"
        )

        assert result.startswith("=" * REPORT_WIDTH)
        assert result.endswith("=" * REPORT_WIDTH)

    def test_contains_summary_section(self) -> None:
        """Standard output includes corpus_id, versions, and pass rate."""
        summary = create_evidence_summary(
            corpus_id="my-corpus",
            baseline_version="v1",
            replay_version="v2",
            total_executions=50,
            passed_count=45,
            pass_rate=0.9,
        )
        recommendation = create_recommendation()

        result = RendererReportCli.render(
            summary, [], recommendation, verbosity="standard"
        )

        assert "my-corpus" in result
        assert "v1" in result
        assert "v2" in result
        assert "45/50" in result

    def test_contains_performance_section(self) -> None:
        """Standard output includes PERFORMANCE section header."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()

        result = RendererReportCli.render(
            summary, [], recommendation, verbosity="standard"
        )

        assert "PERFORMANCE" in result
        assert "Latency:" in result

    def test_contains_recommendation_section(self) -> None:
        """Standard output includes RECOMMENDATION section with confidence."""
        summary = create_evidence_summary()
        recommendation = create_recommendation(action="approve", confidence=0.97)

        result = RendererReportCli.render(
            summary, [], recommendation, verbosity="standard"
        )

        assert "RECOMMENDATION" in result
        assert "APPROVE" in result
        assert "Confidence:" in result

    def test_does_not_include_comparison_details(self) -> None:
        """Standard mode does not include COMPARISON DETAILS even when provided."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()
        comparisons = [create_execution_comparison() for _ in range(3)]

        result = RendererReportCli.render(
            summary, comparisons, recommendation, verbosity="standard"
        )

        assert "COMPARISON DETAILS" not in result

    def test_contains_blockers_when_present(self) -> None:
        """Standard output includes blockers list when recommendation has them."""
        summary = create_evidence_summary()
        recommendation = create_recommendation(
            action="reject",
            blockers=["Critical schema mismatch", "Latency regression > 50%"],
        )

        result = RendererReportCli.render(
            summary, [], recommendation, verbosity="standard"
        )

        assert "Blockers:" in result
        assert "Critical schema mismatch" in result
        assert "Latency regression > 50%" in result

    def test_contains_warnings_when_present(self) -> None:
        """Standard output includes warnings list when recommendation has them."""
        summary = create_evidence_summary()
        recommendation = create_recommendation(
            warnings=["Minor output delta detected"],
        )

        result = RendererReportCli.render(
            summary, [], recommendation, verbosity="standard"
        )

        assert "Warnings:" in result
        assert "Minor output delta detected" in result

    def test_contains_next_steps_when_present(self) -> None:
        """Standard output includes numbered next steps."""
        summary = create_evidence_summary()
        recommendation = create_recommendation(
            next_steps=["Review latency graphs", "Re-run with fixed config"],
        )

        result = RendererReportCli.render(
            summary, [], recommendation, verbosity="standard"
        )

        assert "Next Steps:" in result
        assert "1. Review latency graphs" in result
        assert "2. Re-run with fixed config" in result

    def test_default_verbosity_is_standard(self) -> None:
        """render() without explicit verbosity defaults to 'standard' behavior."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()

        result_default = RendererReportCli.render(summary, [], recommendation)
        result_standard = RendererReportCli.render(
            summary, [], recommendation, verbosity="standard"
        )

        assert result_default == result_standard


# =============================================================================
# render() — verbosity='verbose'
# =============================================================================


class TestRenderVerboseVerbosity:
    """render() with verbosity='verbose' includes comparison rows."""

    def test_includes_comparison_details_section(self) -> None:
        """Verbose output includes COMPARISON DETAILS when comparisons provided."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()
        comparisons = [create_execution_comparison()]

        result = RendererReportCli.render(
            summary, comparisons, recommendation, verbosity="verbose"
        )

        assert "COMPARISON DETAILS" in result

    def test_shows_pass_fail_status_per_comparison(self) -> None:
        """Each comparison row shows [PASS] or [FAIL] status."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()
        pass_cmp = create_execution_comparison(output_match=True)
        fail_cmp = create_execution_comparison(output_match=False)

        result = RendererReportCli.render(
            summary, [pass_cmp, fail_cmp], recommendation, verbosity="verbose"
        )

        assert "[PASS]" in result
        assert "[FAIL]" in result

    def test_caps_comparison_rows_at_limit(self) -> None:
        """Verbose output caps comparison rows at COMPARISON_LIMIT_CLI_VERBOSE."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()
        extra = COMPARISON_LIMIT_CLI_VERBOSE + 3
        comparisons = [create_execution_comparison() for _ in range(extra)]

        result = RendererReportCli.render(
            summary, comparisons, recommendation, verbosity="verbose"
        )

        # The overflow line mentions the remaining count
        assert f"{3} more comparisons" in result

    def test_no_overflow_line_when_within_limit(self) -> None:
        """No overflow line when comparisons <= COMPARISON_LIMIT_CLI_VERBOSE."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()
        comparisons = [
            create_execution_comparison() for _ in range(COMPARISON_LIMIT_CLI_VERBOSE)
        ]

        result = RendererReportCli.render(
            summary, comparisons, recommendation, verbosity="verbose"
        )

        assert "more comparisons" not in result

    def test_empty_comparisons_omits_section(self) -> None:
        """Verbose output with no comparisons omits COMPARISON DETAILS section."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()

        result = RendererReportCli.render(
            summary, [], recommendation, verbosity="verbose"
        )

        assert "COMPARISON DETAILS" not in result

    def test_verbose_shows_info_severity(self) -> None:
        """Verbose mode includes 'info' severity in violation breakdown."""
        violations = create_violation_breakdown(
            total_violations=3,
            by_type={"schema": 3},
            by_severity={"info": 3},
            new_violations=1,
        )
        summary = create_evidence_summary(invariant_violations=violations)
        recommendation = create_recommendation()

        result = RendererReportCli.render(
            summary, [], recommendation, verbosity="verbose"
        )

        assert "info" in result


# =============================================================================
# render() — zero violations
# =============================================================================


class TestRenderZeroViolations:
    """render() with zero violations emits 'No violations detected.'"""

    def test_zero_violations_emits_no_violations_message(self) -> None:
        """When violation count is 0, output says 'No violations detected.'"""
        violations = create_violation_breakdown(total_violations=0)
        summary = create_evidence_summary(invariant_violations=violations)
        recommendation = create_recommendation()

        result = RendererReportCli.render(summary, [], recommendation)

        assert "No violations detected." in result

    def test_zero_violations_omits_severity_line(self) -> None:
        """When violation count is 0, no Severity: line appears."""
        violations = create_violation_breakdown(total_violations=0)
        summary = create_evidence_summary(invariant_violations=violations)
        recommendation = create_recommendation()

        result = RendererReportCli.render(summary, [], recommendation)

        assert "Severity:" not in result


# =============================================================================
# render() — cost_stats present vs absent
# =============================================================================


class TestRenderCostStats:
    """render() emits cost line when cost_stats present, COST_NA_CLI when absent."""

    def test_cost_stats_present_emits_cost_line(self) -> None:
        """When cost_stats is provided, output contains a Cost: line."""
        summary = create_evidence_summary(
            cost_stats=create_cost_stats(baseline_total=1.0, replay_total=1.1)
        )
        recommendation = create_recommendation()

        result = RendererReportCli.render(summary, [], recommendation)

        assert "Cost:" in result
        assert COST_NA_CLI not in result

    def test_cost_stats_absent_emits_cost_na(self) -> None:
        """When cost_stats is None, output contains COST_NA_CLI."""
        summary = create_evidence_summary(cost_stats=None)
        recommendation = create_recommendation()

        result = RendererReportCli.render(summary, [], recommendation)

        assert COST_NA_CLI in result

    def test_cost_sign_positive_when_cost_increased(self) -> None:
        """Cost line includes '+' when replay cost is higher than baseline."""
        summary = create_evidence_summary(
            cost_stats=create_cost_stats(baseline_total=1.0, replay_total=1.5)
        )
        recommendation = create_recommendation()

        result = RendererReportCli.render(summary, [], recommendation)

        # 50% increase should show "+50%"
        assert "+50%" in result

    def test_latency_sign_positive_when_latency_increased(self) -> None:
        """Latency line includes '+' when replay latency is higher."""
        summary = create_evidence_summary(
            latency_stats=create_latency_stats(
                baseline_avg_ms=100.0, replay_avg_ms=120.0
            )
        )
        recommendation = create_recommendation()

        result = RendererReportCli.render(summary, [], recommendation)

        assert "+20%" in result


# =============================================================================
# render() — error handling
# =============================================================================


class TestRenderErrorHandling:
    """render() raises ModelOnexError when comparisons is not a list."""

    def test_raises_when_comparisons_is_not_list(self) -> None:
        """Passing a non-list for comparisons raises ModelOnexError."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()

        with pytest.raises(ModelOnexError):
            RendererReportCli.render(
                summary,
                "not-a-list",  # type: ignore[arg-type]
                recommendation,
            )

    def test_raises_when_comparisons_is_dict(self) -> None:
        """Passing a dict for comparisons raises ModelOnexError."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()

        with pytest.raises(ModelOnexError):
            RendererReportCli.render(
                summary,
                {"key": "value"},  # type: ignore[arg-type]
                recommendation,
            )

    def test_raises_when_comparisons_is_none(self) -> None:
        """Passing None for comparisons raises ModelOnexError."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()

        with pytest.raises(ModelOnexError):
            RendererReportCli.render(
                summary,
                None,  # type: ignore[arg-type]
                recommendation,
            )


# =============================================================================
# _truncate_line
# =============================================================================


class TestTruncateLine:
    """RendererReportCli._truncate_line truncates long lines with ellipsis."""

    def test_short_line_passes_through_unchanged(self) -> None:
        """Lines within REPORT_WIDTH are returned unchanged."""
        line = "A" * (REPORT_WIDTH - 1)
        result = RendererReportCli._truncate_line(line)
        assert result == line

    def test_exact_width_line_passes_through_unchanged(self) -> None:
        """Lines of exactly REPORT_WIDTH chars are returned unchanged."""
        line = "A" * REPORT_WIDTH
        result = RendererReportCli._truncate_line(line)
        assert result == line

    def test_long_line_is_truncated_with_ellipsis(self) -> None:
        """Lines exceeding REPORT_WIDTH are truncated with '...'."""
        line = "A" * (REPORT_WIDTH + 10)
        result = RendererReportCli._truncate_line(line)
        assert result.endswith("...")
        assert len(result) == REPORT_WIDTH

    def test_truncated_line_has_correct_length(self) -> None:
        """Truncated line is exactly max_width characters."""
        line = "x" * 200
        result = RendererReportCli._truncate_line(line, max_width=50)
        assert len(result) == 50

    def test_custom_max_width_respected(self) -> None:
        """Custom max_width parameter is applied correctly."""
        line = "A" * 30
        result = RendererReportCli._truncate_line(line, max_width=20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_empty_string_passes_through(self) -> None:
        """Empty string is returned unchanged."""
        result = RendererReportCli._truncate_line("")
        assert result == ""


# =============================================================================
# render_minimal
# =============================================================================


class TestRenderMinimal:
    """render_minimal returns header + recommendation action line."""

    def test_returns_two_lines(self) -> None:
        """render_minimal produces exactly 2 lines."""
        summary = create_evidence_summary()
        recommendation = create_recommendation()

        result = RendererReportCli.render_minimal(summary, recommendation)

        lines = result.split("\n")
        assert len(lines) == 2

    def test_first_line_is_headline(self) -> None:
        """First line contains the summary headline."""
        summary = create_evidence_summary(
            total_executions=50,
            passed_count=45,
            pass_rate=0.9,
        )
        recommendation = create_recommendation()

        result = RendererReportCli.render_minimal(summary, recommendation)

        first_line = result.split("\n")[0]
        assert "45/50" in first_line

    def test_second_line_contains_recommendation_action(self) -> None:
        """Second line starts with 'Recommendation:' and includes action."""
        summary = create_evidence_summary()
        recommendation = create_recommendation(action="reject", confidence=0.4)

        result = RendererReportCli.render_minimal(summary, recommendation)

        second_line = result.split("\n")[1]
        assert "Recommendation:" in second_line
        assert "REJECT" in second_line

    def test_second_line_contains_confidence(self) -> None:
        """Second line includes the confidence percentage."""
        summary = create_evidence_summary()
        recommendation = create_recommendation(action="approve", confidence=0.95)

        result = RendererReportCli.render_minimal(summary, recommendation)

        second_line = result.split("\n")[1]
        assert "95%" in second_line

    def test_headline_truncated_when_long(self) -> None:
        """A very long corpus_id is truncated in the minimal headline."""
        long_corpus = "x" * (REPORT_WIDTH + 50)
        summary = create_evidence_summary(corpus_id=long_corpus)
        recommendation = create_recommendation()

        result = RendererReportCli.render_minimal(summary, recommendation)

        first_line = result.split("\n")[0]
        assert len(first_line) <= REPORT_WIDTH


# =============================================================================
# _center_text
# =============================================================================


class TestCenterText:
    """RendererReportCli._center_text centers or truncates text."""

    def test_short_text_is_centered(self) -> None:
        """Text shorter than REPORT_WIDTH is padded to be centered."""
        text = "HELLO"
        result = RendererReportCli._center_text(text)
        assert "HELLO" in result
        assert len(result) == REPORT_WIDTH

    def test_exact_width_text_unchanged(self) -> None:
        """Text of exactly REPORT_WIDTH chars is returned unchanged."""
        text = "A" * REPORT_WIDTH
        result = RendererReportCli._center_text(text)
        assert result == text
        assert len(result) == REPORT_WIDTH

    def test_too_long_text_is_truncated_with_ellipsis(self) -> None:
        """Text longer than REPORT_WIDTH is truncated with ellipsis."""
        text = "A" * (REPORT_WIDTH + 5)
        result = RendererReportCli._center_text(text)
        assert result.endswith("...")
        assert len(result) == REPORT_WIDTH


# =============================================================================
# _format_section_header
# =============================================================================


class TestFormatSectionHeader:
    """RendererReportCli._format_section_header appends header + underline."""

    def test_appends_header_and_underline(self) -> None:
        """Header text and a matching underline are appended to lines."""
        lines: list[str] = []
        RendererReportCli._format_section_header("MY SECTION", lines)

        assert lines[0] == "MY SECTION"
        assert lines[1] == "-" * len("MY SECTION")

    def test_underline_length_matches_header(self) -> None:
        """Underline has exactly the same length as the header text."""
        lines: list[str] = []
        header = "PERFORMANCE"
        RendererReportCli._format_section_header(header, lines)

        assert len(lines[1]) == len(header)

    def test_existing_lines_are_preserved(self) -> None:
        """Pre-existing lines in the list are not modified."""
        lines = ["existing line"]
        RendererReportCli._format_section_header("HEADER", lines)

        assert lines[0] == "existing line"
        assert len(lines) == 3


# =============================================================================
# Violation breakdown rendering
# =============================================================================


class TestViolationBreakdown:
    """Violation breakdown including severity and type display."""

    def test_critical_violations_shown(self) -> None:
        """Critical violation count appears in output."""
        violations = create_violation_breakdown(
            total_violations=2,
            by_type={"schema_mismatch": 2},
            by_severity={"critical": 2},
            new_violations=1,
        )
        summary = create_evidence_summary(invariant_violations=violations)
        recommendation = create_recommendation()

        result = RendererReportCli.render(summary, [], recommendation)

        assert "2 critical" in result

    def test_warning_violations_shown(self) -> None:
        """Warning violation count appears in output."""
        violations = create_violation_breakdown(
            total_violations=3,
            by_type={"latency": 3},
            by_severity={"warning": 3},
            new_violations=1,
        )
        summary = create_evidence_summary(invariant_violations=violations)
        recommendation = create_recommendation()

        result = RendererReportCli.render(summary, [], recommendation)

        assert "3 warning" in result

    def test_by_type_breakdown_shown(self) -> None:
        """Violation type breakdown appears with correct counts."""
        violations = create_violation_breakdown(
            total_violations=5,
            by_type={"schema_mismatch": 3, "output_drift": 2},
            by_severity={"critical": 5},
            new_violations=2,
        )
        summary = create_evidence_summary(invariant_violations=violations)
        recommendation = create_recommendation()

        result = RendererReportCli.render(summary, [], recommendation)

        assert "By type:" in result
        assert "schema_mismatch: 3 violation(s)" in result
        assert "output_drift: 2 violation(s)" in result

    def test_severity_normalization_mixed_case(self) -> None:
        """Mixed-case severity keys are aggregated into single display entry."""
        violations = create_violation_breakdown(
            total_violations=5,
            by_type={"test": 5},
            by_severity={"CRITICAL": 3, "Critical": 2},
            new_violations=1,
        )
        summary = create_evidence_summary(invariant_violations=violations)
        recommendation = create_recommendation()

        result = RendererReportCli.render(summary, [], recommendation)

        # Aggregated: 3 + 2 = 5 critical
        assert "5 critical" in result
