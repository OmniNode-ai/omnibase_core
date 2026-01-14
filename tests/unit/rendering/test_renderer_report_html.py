# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for RendererReportHtml (OMN-1200).

This module provides comprehensive tests for the HTML report renderer,
which generates standalone or embedded HTML from evidence summaries
with inline CSS for portability.

Test Coverage:
- Standalone vs embedded HTML modes
- HTML structure validation (doctype, head, body, styles)
- Content section presence (summary, recommendation, violations, performance)
- XSS prevention via HTML escaping
- Recommendation badge styling (approve/review/reject)
- Details section with/without comparisons
- Custom timestamp handling
- Cost data presence/absence

Thread Safety:
    All fixtures create immutable models (frozen=True), making them
    thread-safe for use with pytest-xdist parallel execution.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_invariant_severity import EnumInvariantSeverity
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
from omnibase_core.rendering.renderer_report_html import RendererReportHtml

# =============================================================================
# Helper Functions
# =============================================================================


def create_latency_stats(
    baseline_avg_ms: float = 100.0,
    replay_avg_ms: float = 100.0,
    baseline_p50_ms: float = 95.0,
    replay_p50_ms: float = 95.0,
    baseline_p95_ms: float = 150.0,
    replay_p95_ms: float = 150.0,
) -> ModelLatencyStatistics:
    """Create latency statistics with computed deltas.

    Args:
        baseline_avg_ms: Average baseline latency in ms.
        replay_avg_ms: Average replay latency in ms.
        baseline_p50_ms: Baseline P50 latency in ms.
        replay_p50_ms: Replay P50 latency in ms.
        baseline_p95_ms: Baseline P95 latency in ms.
        replay_p95_ms: Replay P95 latency in ms.

    Returns:
        ModelLatencyStatistics with properly computed delta values.
    """
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
    """Create cost statistics with computed deltas.

    Args:
        baseline_total: Total baseline cost.
        replay_total: Total replay cost.
        execution_count: Number of executions for per-execution averages.

    Returns:
        ModelCostStatistics with properly computed delta values.
    """
    delta_total = replay_total - baseline_total
    delta_percent = (
        (delta_total / baseline_total * 100.0) if baseline_total != 0 else 0.0
    )

    # Guard against division by zero when execution_count is 0
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
    """Create an invariant violation breakdown.

    Args:
        total_violations: Total number of violations.
        by_type: Violations grouped by type.
        by_severity: Violations grouped by severity.
        new_violations: New violations (regressions).
        new_critical_violations: New critical violations.
        fixed_violations: Fixed violations (improvements).

    Returns:
        ModelInvariantViolationBreakdown instance.
    """
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
    """Create an evidence summary for testing.

    Args:
        corpus_id: Corpus identifier.
        baseline_version: Baseline version string.
        replay_version: Replay version string.
        total_executions: Total number of comparisons.
        passed_count: Number of passed comparisons.
        failed_count: Number of failed comparisons.
        pass_rate: Pass rate (0.0 - 1.0).
        confidence_score: Confidence score (0.0 - 1.0).
        recommendation: Suggested action.
        latency_stats: Latency statistics (created if None).
        cost_stats: Cost statistics (None if not provided).
        invariant_violations: Violation breakdown (created if None).

    Returns:
        ModelEvidenceSummary instance.
    """
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
    severity: EnumInvariantSeverity = EnumInvariantSeverity.INFO,
    invariant_name: str = "test_invariant",
) -> ModelInvariantResult:
    """Create an invariant result for testing.

    Args:
        passed: Whether the invariant passed.
        severity: Severity level of the invariant.
        invariant_name: Name of the invariant.

    Returns:
        ModelInvariantResult instance.
    """
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
    """Create an execution comparison for testing.

    Args:
        output_match: Whether outputs matched.
        baseline_passed: Whether baseline passed.
        replay_passed: Whether replay passed.
        baseline_latency_ms: Baseline execution time.
        replay_latency_ms: Replay execution time.
        baseline_cost: Baseline cost (optional).
        replay_cost: Replay cost (optional).

    Returns:
        ModelExecutionComparison instance.
    """
    baseline_id = uuid4()
    replay_id = uuid4()
    hash_value = "abc123"
    replay_hash = "abc123" if output_match else "def456"

    # Calculate latency deltas
    latency_delta_ms = replay_latency_ms - baseline_latency_ms
    latency_delta_percent = (
        (latency_delta_ms / baseline_latency_ms * 100.0)
        if baseline_latency_ms != 0
        else 0.0
    )

    # Calculate cost deltas if both costs provided
    cost_delta = None
    cost_delta_percent = None
    if baseline_cost is not None and replay_cost is not None:
        cost_delta = replay_cost - baseline_cost
        cost_delta_percent = (
            (cost_delta / baseline_cost * 100.0) if baseline_cost != 0 else 0.0
        )

    # Create invariant results
    baseline_results = [create_invariant_result(passed=baseline_passed)]
    replay_results = [create_invariant_result(passed=replay_passed)]

    # Create comparison summary
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
    """Create a sample evidence summary for testing.

    Returns:
        ModelEvidenceSummary with mixed results (47/50 passed, 3 violations).
    """
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
            replay_avg_ms=82.0,  # 18% improvement
        ),
        cost_stats=create_cost_stats(
            baseline_total=10.0,
            replay_total=5.8,  # 42% improvement
        ),
    )


@pytest.fixture
def sample_recommendation() -> ModelDecisionRecommendation:
    """Create a sample recommendation for testing.

    Returns:
        ModelDecisionRecommendation with approve action.
    """
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
    """Create sample comparisons for testing.

    Returns:
        List of ModelExecutionComparison with mixed pass/fail results.
    """
    comparisons = []

    # 8 passing comparisons
    for i in range(8):
        comparisons.append(
            create_execution_comparison(
                output_match=True,
                baseline_passed=True,
                replay_passed=True,
                baseline_latency_ms=100.0 + i * 5,
                replay_latency_ms=85.0 + i * 5,  # Faster
            )
        )

    # 2 failing comparisons
    for i in range(2):
        comparisons.append(
            create_execution_comparison(
                output_match=False,
                baseline_passed=True,
                replay_passed=False,
                baseline_latency_ms=110.0,
                replay_latency_ms=130.0,  # Slower
            )
        )

    return comparisons


# =============================================================================
# Tests: HTML Structure
# =============================================================================


class TestRendererReportHtmlStructure:
    """Tests for HTML document structure."""

    def test_render_standalone_html(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Standalone mode should produce full HTML document."""
        html = RendererReportHtml.render(
            sample_summary,
            sample_comparisons,
            sample_recommendation,
            standalone=True,
        )
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "<style>" in html
        assert "<body>" in html
        assert "</body>" in html

    def test_render_embedded_html(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Embedded mode should produce just content div."""
        html = RendererReportHtml.render(
            sample_summary,
            sample_comparisons,
            sample_recommendation,
            standalone=False,
        )
        assert "<!DOCTYPE html>" not in html
        assert "<html" not in html
        assert "<head>" not in html
        assert 'class="evidence-report"' in html

    def test_render_is_valid_html(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Output should be well-formed HTML (basic structural checks)."""
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, sample_recommendation
        )
        # Basic structure checks - ensure matching open/close tags
        assert html.count("<table>") == html.count("</table>")
        assert html.count("<tr>") == html.count("</tr>")
        assert html.count("<td>") == html.count("</td>")
        assert html.count("<th>") == html.count("</th>")
        assert html.count("<ul>") == html.count("</ul>")
        assert html.count("<ol>") == html.count("</ol>")
        # Note: <li> may have inline styles so simple count won't work
        assert html.count("</li>") > 0  # Has list items
        assert html.count("<details>") == html.count("</details>")


# =============================================================================
# Tests: Content Sections
# =============================================================================


class TestRendererReportHtmlContent:
    """Tests for HTML content sections."""

    def test_render_contains_summary_section(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Output should contain summary section."""
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, sample_recommendation
        )
        assert "Summary" in html
        assert sample_summary.corpus_id in html
        assert sample_summary.baseline_version in html
        assert sample_summary.replay_version in html
        # Check pass rate display
        assert (
            f"{sample_summary.passed_count}/{sample_summary.total_executions}" in html
        )

    def test_render_contains_recommendation_section(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Output should contain recommendation section."""
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, sample_recommendation
        )
        assert "Recommendation" in html
        assert "APPROVE" in html  # action.upper()
        assert "95%" in html  # confidence

    def test_render_contains_violations_section(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Output should contain violations section."""
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, sample_recommendation
        )
        assert "Invariant Violations" in html
        # Should show violation count
        assert "3 violation" in html

    def test_render_contains_performance_section(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Output should contain performance section."""
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, sample_recommendation
        )
        assert "Performance" in html
        assert "Latency" in html
        assert "Cost" in html

    def test_render_with_rationale(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Recommendation rationale should appear in output."""
        recommendation = ModelDecisionRecommendation(
            action="review",
            confidence=0.85,
            blockers=[],
            warnings=[],
            next_steps=[],
            rationale="Latency regression detected in production workload.",
        )
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, recommendation
        )
        assert "Latency regression detected in production workload" in html

    def test_render_with_blockers(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Blockers should appear in output."""
        recommendation = ModelDecisionRecommendation(
            action="reject",
            confidence=0.5,
            blockers=["Critical invariant failure", "Data corruption detected"],
            warnings=[],
            next_steps=[],
            rationale="",
        )
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, recommendation
        )
        assert "Blockers" in html
        assert "Critical invariant failure" in html
        assert "Data corruption detected" in html

    def test_render_with_warnings(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Warnings should appear in output."""
        recommendation = ModelDecisionRecommendation(
            action="review",
            confidence=0.85,
            blockers=[],
            warnings=["Minor latency regression", "Cost increase 15%"],
            next_steps=[],
            rationale="",
        )
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, recommendation
        )
        assert "Warnings" in html
        assert "Minor latency regression" in html
        assert "Cost increase 15%" in html

    def test_render_with_next_steps(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Next steps should appear as ordered list."""
        recommendation = ModelDecisionRecommendation(
            action="approve",
            confidence=0.95,
            blockers=[],
            warnings=[],
            next_steps=["Review test coverage", "Deploy to staging", "Monitor metrics"],
            rationale="",
        )
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, recommendation
        )
        assert "Next Steps" in html
        assert "Review test coverage" in html
        assert "Deploy to staging" in html
        assert "Monitor metrics" in html
        assert "<ol>" in html  # Ordered list


# =============================================================================
# Tests: Security (XSS Prevention)
# =============================================================================


class TestRendererReportHtmlSecurity:
    """Tests for HTML escaping and XSS prevention."""

    def test_render_escapes_html_in_corpus_id(
        self,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """User content in corpus_id should be HTML-escaped (XSS prevention)."""
        summary = create_evidence_summary(
            corpus_id="<script>alert('xss')</script>",
        )
        html = RendererReportHtml.render(
            summary, sample_comparisons, sample_recommendation
        )
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_render_escapes_html_in_versions(
        self,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Version strings should be HTML-escaped."""
        summary = create_evidence_summary(
            baseline_version="<img onerror='alert(1)' src=x>",
            replay_version="<b onmouseover='alert(2)'>v2</b>",
        )
        html = RendererReportHtml.render(
            summary, sample_comparisons, sample_recommendation
        )
        assert "<img" not in html
        assert "<b onmouseover" not in html
        assert "&lt;img" in html

    def test_render_escapes_html_in_recommendation_rationale(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Recommendation rationale should be HTML-escaped."""
        recommendation = ModelDecisionRecommendation(
            action="review",
            confidence=0.85,
            blockers=[],
            warnings=[],
            next_steps=[],
            rationale="<script>document.cookie</script>",
        )
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, recommendation
        )
        assert "<script>document.cookie</script>" not in html
        assert "&lt;script&gt;" in html

    def test_render_escapes_html_in_blockers(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Blockers list should be HTML-escaped."""
        recommendation = ModelDecisionRecommendation(
            action="reject",
            confidence=0.5,
            blockers=["<script>evil()</script>"],
            warnings=[],
            next_steps=[],
            rationale="",
        )
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, recommendation
        )
        assert "<script>evil()</script>" not in html
        assert "&lt;script&gt;" in html

    def test_render_escapes_html_in_warnings(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Warnings list should be HTML-escaped."""
        recommendation = ModelDecisionRecommendation(
            action="review",
            confidence=0.85,
            blockers=[],
            warnings=['<img src="x" onerror="alert(1)">'],
            next_steps=[],
            rationale="",
        )
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, recommendation
        )
        assert '<img src="x"' not in html
        assert "&lt;img" in html

    def test_render_escapes_html_in_next_steps(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Next steps list should be HTML-escaped."""
        recommendation = ModelDecisionRecommendation(
            action="approve",
            confidence=0.95,
            blockers=[],
            warnings=[],
            next_steps=["<a href='javascript:alert(1)'>Click me</a>"],
            rationale="",
        )
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, recommendation
        )
        # The <a tag should be escaped - unescaped <a would be executable
        assert "<a href=" not in html
        assert "&lt;a href" in html
        # The quotes are also escaped
        assert "&#x27;" in html  # Escaped single quote


# =============================================================================
# Tests: Recommendation Badges
# =============================================================================


class TestRendererReportHtmlBadges:
    """Tests for recommendation badge styling."""

    def test_render_approve_badge(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Approve recommendation should have success badge."""
        recommendation = ModelDecisionRecommendation(
            action="approve",
            confidence=0.95,
            blockers=[],
            warnings=[],
            next_steps=[],
            rationale="",
        )
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, recommendation
        )
        assert "badge-success" in html
        assert "APPROVE" in html

    def test_render_review_badge(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Review recommendation should have warning badge."""
        recommendation = ModelDecisionRecommendation(
            action="review",
            confidence=0.85,
            blockers=[],
            warnings=[],
            next_steps=[],
            rationale="",
        )
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, recommendation
        )
        assert "badge-warning" in html
        assert "REVIEW" in html

    def test_render_reject_badge(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Reject recommendation should have danger badge."""
        recommendation = ModelDecisionRecommendation(
            action="reject",
            confidence=0.5,
            blockers=["Critical failure"],
            warnings=[],
            next_steps=[],
            rationale="",
        )
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, recommendation
        )
        assert "badge-danger" in html
        assert "REJECT" in html


# =============================================================================
# Tests: Details Section
# =============================================================================


class TestRendererReportHtmlDetails:
    """Tests for comparison details section."""

    def test_render_with_details(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """include_details=True should show comparison table."""
        html = RendererReportHtml.render(
            sample_summary,
            sample_comparisons,
            sample_recommendation,
            include_details=True,
        )
        assert "Comparison Details" in html
        assert "<details>" in html
        assert "</details>" in html
        assert "Click to expand" in html

    def test_render_without_details(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """include_details=False should hide comparison table."""
        html = RendererReportHtml.render(
            sample_summary,
            sample_comparisons,
            sample_recommendation,
            include_details=False,
        )
        assert "Comparison Details" not in html
        assert "<details>" not in html

    def test_render_details_with_empty_comparisons(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
    ) -> None:
        """Empty comparisons list should not show details even with include_details=True."""
        html = RendererReportHtml.render(
            sample_summary,
            [],  # Empty comparisons
            sample_recommendation,
            include_details=True,
        )
        # Details section only renders when comparisons is non-empty
        assert "Comparison Details" not in html

    def test_render_details_shows_comparison_status(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Details section should show pass/fail status for comparisons."""
        html = RendererReportHtml.render(
            sample_summary,
            sample_comparisons,
            sample_recommendation,
            include_details=True,
        )
        # Should show PASS badges for matching outputs
        assert "PASS" in html
        # Should show FAIL badges for non-matching outputs
        assert "FAIL" in html


# =============================================================================
# Tests: Timestamps
# =============================================================================


class TestRendererReportHtmlTimestamps:
    """Tests for timestamp handling."""

    def test_render_custom_timestamp(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Custom generated_at should appear in output."""
        custom_time = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        html = RendererReportHtml.render(
            sample_summary,
            sample_comparisons,
            sample_recommendation,
            generated_at=custom_time,
        )
        assert "2025-01-15T10:30:00" in html

    def test_render_default_timestamp(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Default timestamp should be current time (ISO format)."""
        html = RendererReportHtml.render(
            sample_summary,
            sample_comparisons,
            sample_recommendation,
        )
        # Should contain Generated: with an ISO timestamp
        assert "Generated:" in html
        # Check for ISO format pattern (YYYY-MM-DDTHH:MM:SS)
        import re

        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", html)


# =============================================================================
# Tests: Timezone Validation
# =============================================================================


class TestRendererReportHtmlTimezoneValidation:
    """Tests for timezone validation in HTML renderer."""

    def test_render_rejects_timezone_naive_datetime(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Timezone-naive datetime should raise ValueError."""
        naive_dt = datetime(2025, 1, 15, 10, 30, 0)  # No tzinfo
        with pytest.raises(ValueError, match="timezone-aware"):
            RendererReportHtml.render(
                sample_summary,
                sample_comparisons,
                sample_recommendation,
                generated_at=naive_dt,
            )

    def test_render_accepts_timezone_aware_datetime(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Timezone-aware datetime should be accepted."""
        aware_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        html = RendererReportHtml.render(
            sample_summary,
            sample_comparisons,
            sample_recommendation,
            generated_at=aware_dt,
        )
        assert "2025-01-15T10:30:00" in html


# =============================================================================
# Tests: Cost Statistics
# =============================================================================


class TestRendererReportHtmlCostStats:
    """Tests for cost statistics handling."""

    def test_render_with_cost_stats(
        self,
        sample_summary: ModelEvidenceSummary,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Summary with cost_stats should show cost data."""
        # sample_summary fixture includes cost_stats
        html = RendererReportHtml.render(
            sample_summary, sample_comparisons, sample_recommendation
        )
        assert "Cost" in html
        # Should show cost values with $ prefix
        assert "$" in html

    def test_render_no_cost_stats(
        self,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Missing cost stats should show placeholder message."""
        summary = create_evidence_summary(
            cost_stats=None,  # No cost data
        )
        html = RendererReportHtml.render(
            summary, sample_comparisons, sample_recommendation
        )
        assert "Cost data not available" in html


# =============================================================================
# Tests: Violations Section
# =============================================================================


class TestRendererReportHtmlViolations:
    """Tests for violations section rendering."""

    def test_render_no_violations(
        self,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """No violations should show success badge."""
        summary = create_evidence_summary(
            invariant_violations=create_violation_breakdown(
                total_violations=0,
            ),
        )
        html = RendererReportHtml.render(
            summary, sample_comparisons, sample_recommendation
        )
        assert "No violations detected" in html
        assert "badge-success" in html

    def test_render_violations_by_type(
        self,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Violations by type should be displayed."""
        summary = create_evidence_summary(
            invariant_violations=create_violation_breakdown(
                total_violations=5,
                by_type={"output_mismatch": 3, "latency_regression": 2},
                new_violations=2,
            ),
        )
        html = RendererReportHtml.render(
            summary, sample_comparisons, sample_recommendation
        )
        assert "By Type" in html
        assert "output_mismatch" in html
        assert "latency_regression" in html

    def test_render_violations_by_severity(
        self,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Violations by severity should be displayed."""
        summary = create_evidence_summary(
            invariant_violations=create_violation_breakdown(
                total_violations=4,
                by_severity={"critical": 1, "warning": 3},
                new_violations=1,
            ),
        )
        html = RendererReportHtml.render(
            summary, sample_comparisons, sample_recommendation
        )
        assert "By Severity" in html
        # Severity should be capitalized
        assert "Critical" in html
        assert "Warning" in html


# =============================================================================
# Tests: Performance Metrics
# =============================================================================


class TestRendererReportHtmlPerformance:
    """Tests for performance metrics rendering."""

    def test_render_latency_improvement(
        self,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Latency improvement should show positive class."""
        summary = create_evidence_summary(
            latency_stats=create_latency_stats(
                baseline_avg_ms=100.0,
                replay_avg_ms=80.0,  # 20% improvement
            ),
        )
        html = RendererReportHtml.render(
            summary, sample_comparisons, sample_recommendation
        )
        # Negative delta (improvement) should use positive class
        assert "metric-positive" in html

    def test_render_latency_regression(
        self,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Latency regression should show negative class."""
        summary = create_evidence_summary(
            latency_stats=create_latency_stats(
                baseline_avg_ms=100.0,
                replay_avg_ms=120.0,  # 20% regression
            ),
        )
        html = RendererReportHtml.render(
            summary, sample_comparisons, sample_recommendation
        )
        # Positive delta (regression) should use negative class
        assert "metric-negative" in html


# =============================================================================
# Tests: Edge Cases
# =============================================================================


class TestRendererReportHtmlEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_render_minimal_summary(
        self,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Minimal summary with defaults should render successfully."""
        summary = create_evidence_summary()
        recommendation = ModelDecisionRecommendation(
            action="review",
            confidence=0.90,
            blockers=[],
            warnings=[],
            next_steps=[],
            rationale="",
        )
        html = RendererReportHtml.render(summary, sample_comparisons, recommendation)
        assert "evidence-report" in html
        assert "Summary" in html

    def test_render_perfect_score_summary(
        self,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Perfect score summary should render with approve badge."""
        summary = create_evidence_summary(
            total_executions=100,
            passed_count=100,
            failed_count=0,
            pass_rate=1.0,
            confidence_score=1.0,
            recommendation="approve",
            invariant_violations=create_violation_breakdown(total_violations=0),
        )
        recommendation = ModelDecisionRecommendation(
            action="approve",
            confidence=1.0,
            blockers=[],
            warnings=[],
            next_steps=[],
            rationale="",
        )
        html = RendererReportHtml.render(summary, sample_comparisons, recommendation)
        assert "badge-success" in html
        assert "100/100" in html

    def test_render_special_characters_in_corpus_id(
        self,
        sample_recommendation: ModelDecisionRecommendation,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Special characters in corpus_id should be escaped."""
        summary = create_evidence_summary(
            corpus_id="test&corpus<id>with\"quotes'",
        )
        html = RendererReportHtml.render(
            summary, sample_comparisons, sample_recommendation
        )
        # Should be escaped
        assert "&amp;" in html
        assert "&lt;" in html
        assert "&gt;" in html
        assert "&quot;" in html
