# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Comprehensive TDD test suite for ServiceDecisionReportGenerator (OMN-1199).

This module provides TDD tests for the decision report generation service,
which generates CLI, JSON, and Markdown reports from evidence summaries
and execution comparisons with actionable recommendations.

Test Coverage:
- CLI format generation (minimal, standard, verbose verbosity)
- JSON format generation (structure, serialization, schema compliance)
- Markdown format generation (structure, tables, code blocks, links)
- Report structure (executive summary, findings, recommendations)
- Recommendation logic (approve/review/reject conditions)

Thread Safety:
    All fixtures create immutable models (frozen=True), making them
    thread-safe for use with pytest-xdist parallel execution.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_invariant_severity import EnumInvariantSeverity
from omnibase_core.models.comparison.model_execution_comparison import (
    ModelExecutionComparison,
)
from omnibase_core.models.comparison.model_invariant_comparison_summary import (
    ModelInvariantComparisonSummary,
)
from omnibase_core.models.evidence.model_cost_statistics import ModelCostStatistics

# =============================================================================
# Service and Model Imports (TDD - services don't exist yet)
# =============================================================================
# Import service and model (now implemented)
from omnibase_core.models.evidence.model_evidence_summary import ModelEvidenceSummary
from omnibase_core.models.evidence.model_invariant_violation_breakdown import (
    ModelInvariantViolationBreakdown,
)
from omnibase_core.models.evidence.model_latency_statistics import (
    ModelLatencyStatistics,
)
from omnibase_core.models.invariant.model_invariant_result import ModelInvariantResult
from omnibase_core.services.service_decision_report_generator import (
    ServiceDecisionReportGenerator,
)

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
) -> ModelCostStatistics:
    """Create cost statistics with computed deltas.

    Args:
        baseline_total: Total baseline cost.
        replay_total: Total replay cost.

    Returns:
        ModelCostStatistics with properly computed delta values.
    """
    delta_total = replay_total - baseline_total
    delta_percent = (
        (delta_total / baseline_total * 100.0) if baseline_total != 0 else 0.0
    )

    return ModelCostStatistics(
        baseline_total=baseline_total,
        replay_total=replay_total,
        delta_total=delta_total,
        delta_percent=delta_percent,
        baseline_avg_per_execution=baseline_total / 10,  # Assume 10 executions
        replay_avg_per_execution=replay_total / 10,
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
    recommendation: Literal["approve", "review", "reject"] = "review",
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
        recommendation=recommendation,
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
    hash_value = "abc123"  # Baseline hash is always the same
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
def sample_evidence_summary() -> ModelEvidenceSummary:
    """Create a sample evidence summary with realistic data.

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
def sample_comparisons() -> list[ModelExecutionComparison]:
    """Create a list of sample execution comparisons with varied results.

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
    comparisons.append(
        create_execution_comparison(
            output_match=False,
            baseline_passed=True,
            replay_passed=False,
            baseline_latency_ms=100.0,
            replay_latency_ms=150.0,  # Slower
        )
    )
    comparisons.append(
        create_execution_comparison(
            output_match=False,
            baseline_passed=True,
            replay_passed=False,
            baseline_latency_ms=110.0,
            replay_latency_ms=200.0,  # Much slower
        )
    )

    return comparisons


@pytest.fixture
def passing_evidence_summary() -> ModelEvidenceSummary:
    """Create an evidence summary with all passing results.

    Returns:
        ModelEvidenceSummary with high confidence and all passing.
    """
    return create_evidence_summary(
        total_executions=100,
        passed_count=100,
        failed_count=0,
        pass_rate=1.0,
        confidence_score=0.98,
        recommendation="approve",
        invariant_violations=create_violation_breakdown(
            total_violations=0,
            by_type={},
            by_severity={},
            new_violations=0,
            new_critical_violations=0,
            fixed_violations=2,  # Fixed some issues
        ),
        latency_stats=create_latency_stats(
            baseline_avg_ms=100.0,
            replay_avg_ms=90.0,  # 10% improvement
        ),
        cost_stats=create_cost_stats(
            baseline_total=10.0,
            replay_total=8.0,  # 20% improvement
        ),
    )


@pytest.fixture
def failing_evidence_summary() -> ModelEvidenceSummary:
    """Create an evidence summary with critical failures.

    Returns:
        ModelEvidenceSummary with low confidence and critical failures.
    """
    return create_evidence_summary(
        total_executions=50,
        passed_count=25,
        failed_count=25,
        pass_rate=0.50,
        confidence_score=0.25,
        recommendation="reject",
        invariant_violations=create_violation_breakdown(
            total_violations=25,
            by_type={"output_equivalence": 15, "schema": 10},
            by_severity={"critical": 10, "warning": 15},
            new_violations=20,
            new_critical_violations=10,
            fixed_violations=0,
        ),
        latency_stats=create_latency_stats(
            baseline_avg_ms=100.0,
            replay_avg_ms=200.0,  # 100% regression
        ),
        cost_stats=create_cost_stats(
            baseline_total=10.0,
            replay_total=25.0,  # 150% increase
        ),
    )


@pytest.fixture
def mixed_evidence_summary() -> ModelEvidenceSummary:
    """Create an evidence summary with warnings but no blockers.

    Returns:
        ModelEvidenceSummary with medium confidence and warnings only.
    """
    return create_evidence_summary(
        total_executions=50,
        passed_count=45,
        failed_count=5,
        pass_rate=0.90,
        confidence_score=0.85,
        recommendation="review",
        invariant_violations=create_violation_breakdown(
            total_violations=5,
            by_type={"latency": 3, "cost": 2},
            by_severity={"warning": 5},
            new_violations=3,
            new_critical_violations=0,
            fixed_violations=2,
        ),
        latency_stats=create_latency_stats(
            baseline_avg_ms=100.0,
            replay_avg_ms=115.0,  # 15% regression (minor)
        ),
    )


@pytest.fixture
def service() -> ServiceDecisionReportGenerator:
    """Create a ServiceDecisionReportGenerator instance.

    Returns:
        Configured ServiceDecisionReportGenerator.
    """
    return ServiceDecisionReportGenerator()


# =============================================================================
# CLI Format Tests
# =============================================================================


@pytest.mark.unit
class TestCLIFormat:
    """Test CLI report generation."""

    def test_minimal_verbosity(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test minimal verbosity CLI output shows only essential info."""
        report = service.generate_cli_report(
            sample_evidence_summary,
            sample_comparisons,
            verbosity="minimal",
        )

        # Minimal should include: recommendation from service, pass rate, confidence
        # Service generates its own recommendation via generate_recommendation()
        recommendation = service.generate_recommendation(sample_evidence_summary)
        assert recommendation.action.upper() in report
        assert "47" in report and "50" in report  # Pass counts
        # Should NOT include detailed breakdown
        assert "violation breakdown" not in report.lower()

    def test_standard_verbosity(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test standard verbosity CLI output shows summary and key metrics."""
        report = service.generate_cli_report(
            sample_evidence_summary,
            sample_comparisons,
            verbosity="standard",
        )

        # Standard should include recommendation from service and metrics
        recommendation = service.generate_recommendation(sample_evidence_summary)
        assert recommendation.action.upper() in report
        assert "47" in report and "50" in report  # Pass counts
        assert "latency" in report.lower()

    def test_verbose_output(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test verbose CLI output shows all details including comparisons."""
        report = service.generate_cli_report(
            sample_evidence_summary,
            sample_comparisons,
            verbosity="verbose",
        )

        # Verbose should include detailed breakdown
        recommendation = service.generate_recommendation(sample_evidence_summary)
        assert recommendation.action.upper() in report
        assert "violation" in report.lower()
        assert sample_evidence_summary.corpus_id in report

    def test_cli_width_formatting(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Verify no CLI line exceeds 80 characters."""
        report = service.generate_cli_report(
            sample_evidence_summary,
            sample_comparisons,
            verbosity="standard",
        )

        for i, line in enumerate(report.split("\n"), 1):
            assert len(line) <= 80, (
                f"Line {i} too long: {len(line)} chars (max 80). "
                f"Content: {line[:50]}..."
            )

    def test_color_codes_optional(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that CLI report does not contain ANSI color codes by default."""
        # Current implementation does not use colors
        report = service.generate_cli_report(
            sample_evidence_summary,
            sample_comparisons,
            verbosity="standard",
        )

        # Should not contain ANSI escape codes (no color by default)
        assert "\x1b[" not in report
        assert "\033[" not in report
        assert isinstance(report, str)


# =============================================================================
# JSON Format Tests
# =============================================================================


@pytest.mark.unit
class TestJSONFormat:
    """Test JSON report generation."""

    def test_json_structure(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test JSON report has required structure."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        # Required top-level keys
        assert "summary" in report
        assert "recommendation" in report
        assert "performance" in report
        assert "violations" in report
        assert "generated_at" in report

        # Recommendation structure
        rec = report["recommendation"]
        assert "action" in rec
        assert rec["action"] in ("approve", "review", "reject")

    def test_json_without_details(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test JSON report without detailed comparison data."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
            include_details=False,
        )

        # Should have summary but not individual comparison details
        assert "summary" in report
        assert "details" not in report

    def test_json_with_details(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test JSON report with detailed comparison data."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
            include_details=True,
        )

        # Should include details
        assert "details" in report
        assert isinstance(report["details"], list)
        assert len(report["details"]) == len(sample_comparisons)

    def test_json_serializable(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Verify JSON output is valid and serializable."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
            include_details=True,
        )

        # Should not raise when serializing to JSON string
        json_str = json.dumps(report, default=str)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Should be parseable back
        parsed = json.loads(json_str)
        assert parsed["recommendation"]["action"] == report["recommendation"]["action"]

    def test_json_schema_compliance(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test JSON report complies with expected schema structure."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        # Validate summary section
        summary = report["summary"]
        assert "corpus_id" in summary
        assert "baseline_version" in summary
        assert "replay_version" in summary
        assert "pass_rate" in summary
        assert "confidence_score" in summary

        # Validate performance section
        performance = report["performance"]
        assert "latency" in performance

        # Validate violations section
        violations = report["violations"]
        assert "total" in violations

        # Validate recommendation section
        rec = report["recommendation"]
        assert isinstance(rec["action"], str)
        assert "rationale" in rec


# =============================================================================
# Markdown Format Tests
# =============================================================================


@pytest.mark.unit
class TestMarkdownFormat:
    """Test Markdown report generation."""

    def test_markdown_structure(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test Markdown report has proper structure with headers."""
        report = service.generate_markdown_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        # Should have main header
        assert "# " in report or "## " in report

        # Should have key sections
        assert "summary" in report.lower() or "overview" in report.lower()
        assert "recommendation" in report.lower()

    def test_markdown_tables_formatted(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test Markdown tables are properly formatted."""
        report = service.generate_markdown_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        # Should have table formatting (pipes and dashes)
        assert "|" in report
        # Table header separator line
        lines = report.split("\n")
        table_separator_found = any(
            line.strip().startswith("|") and "---" in line for line in lines
        )
        assert table_separator_found, "Markdown table separator (|---|) not found"

    def test_markdown_code_blocks(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test Markdown code blocks are properly formatted if present."""
        report = service.generate_markdown_report(
            sample_evidence_summary,
            sample_comparisons,
            include_details=True,
        )

        # Should have code block delimiters if code blocks are present
        # Code blocks start with ``` and end with ```
        if "```" in report:
            # Count opening and closing - should be even (pairs)
            code_block_count = report.count("```")
            assert code_block_count % 2 == 0, (
                f"Unmatched code block delimiters: found {code_block_count}"
            )

    def test_markdown_links_valid(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test Markdown links are valid format."""
        report = service.generate_markdown_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        # Find all markdown links [text](url)
        import re

        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", report)

        for text, url in links:
            # Text should not be empty
            assert len(text) > 0, f"Empty link text found: [{text}]({url})"
            # URL should not be empty and should look like a URL or anchor
            assert len(url) > 0, f"Empty URL found: [{text}]({url})"
            assert url.startswith(("#", "http", "/", "./")), (
                f"Invalid URL format: {url}"
            )


# =============================================================================
# Report Structure Tests
# =============================================================================


@pytest.mark.unit
class TestReportStructure:
    """Test report content structure."""

    def test_executive_summary_present(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that executive summary is present in report."""
        json_report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        # Executive summary should contain headline info
        assert "summary" in json_report
        summary = json_report["summary"]

        # Key executive metrics
        assert "pass_rate" in summary
        assert "confidence_score" in summary
        assert "total_executions" in summary

    def test_findings_section_present(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that findings section is present with violation details."""
        json_report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        # Findings should include violations and performance
        assert "violations" in json_report
        assert "performance" in json_report
        violations = json_report["violations"]
        assert "total" in violations

    def test_recommendation_section_present(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that recommendation section is present with action."""
        json_report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        assert "recommendation" in json_report
        rec = json_report["recommendation"]
        assert "action" in rec
        assert rec["action"] in ("approve", "review", "reject")

    def test_blockers_listed(
        self,
        service: ServiceDecisionReportGenerator,
        failing_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that blockers are listed for reject recommendations."""
        json_report = service.generate_json_report(
            failing_evidence_summary,
            sample_comparisons,
        )

        rec = json_report["recommendation"]

        # Should have blockers when recommendation is reject
        if rec["action"] == "reject":
            assert "blockers" in rec
            blockers = rec["blockers"]
            assert isinstance(blockers, list)
            assert len(blockers) > 0

    def test_next_steps_actionable(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that next steps are present and actionable."""
        json_report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        rec = json_report["recommendation"]
        assert "next_steps" in rec

        next_steps = rec["next_steps"]
        assert isinstance(next_steps, list)
        # Should have at least one next step
        assert len(next_steps) >= 1

        # Each step should be a non-empty string
        for step in next_steps:
            assert isinstance(step, str)
            assert len(step) > 0


# =============================================================================
# Recommendation Logic Tests
# =============================================================================


@pytest.mark.unit
class TestRecommendationLogic:
    """Test recommendation generation logic."""

    def test_approve_conditions(
        self,
        service: ServiceDecisionReportGenerator,
        passing_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test approve conditions: high confidence + no critical violations."""
        rec = service.generate_recommendation(passing_evidence_summary)

        # High confidence (0.98) + no critical = approve
        assert rec.action == "approve"

    def test_review_conditions(
        self,
        service: ServiceDecisionReportGenerator,
        mixed_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test review conditions: medium confidence or warnings."""
        rec = service.generate_recommendation(mixed_evidence_summary)

        # Medium confidence (0.85) + warnings = review
        assert rec.action == "review"

    def test_reject_conditions(
        self,
        service: ServiceDecisionReportGenerator,
        failing_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test reject conditions: low confidence OR critical violations."""
        rec = service.generate_recommendation(failing_evidence_summary)

        # Low confidence (0.25) + critical violations = reject
        assert rec.action == "reject"

    def test_reasoning_included(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test that rationale is included in recommendation."""
        rec = service.generate_recommendation(sample_evidence_summary)

        # Rationale should explain the decision
        assert hasattr(rec, "rationale")
        assert isinstance(rec.rationale, str)
        assert len(rec.rationale) > 0

    def test_blockers_from_critical_violations(
        self,
        service: ServiceDecisionReportGenerator,
        failing_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test that blockers are populated from critical violations."""
        rec = service.generate_recommendation(failing_evidence_summary)

        # Failing summary has new_critical_violations > 0
        assert hasattr(rec, "blockers")
        assert isinstance(rec.blockers, list)
        # Should have blockers for critical violations
        assert len(rec.blockers) > 0

    def test_warnings_from_non_critical(
        self,
        service: ServiceDecisionReportGenerator,
        mixed_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test that warnings are populated from non-critical violations."""
        rec = service.generate_recommendation(mixed_evidence_summary)

        # Mixed summary has warnings but no critical
        assert hasattr(rec, "warnings")
        assert isinstance(rec.warnings, list)

    def test_next_steps_context_aware(
        self,
        service: ServiceDecisionReportGenerator,
    ) -> None:
        """Test that next steps are context-aware based on recommendation."""
        # Test approve case
        passing_summary = create_evidence_summary(
            passed_count=100,
            failed_count=0,
            pass_rate=1.0,
            confidence_score=0.99,
            recommendation="approve",
        )
        rec_approve = service.generate_recommendation(passing_summary)
        assert any(
            "deploy" in step.lower()
            or "proceed" in step.lower()
            or "merge" in step.lower()
            for step in rec_approve.next_steps
        ), f"Approve next steps should mention deployment: {rec_approve.next_steps}"

        # Test reject case
        failing_summary = create_evidence_summary(
            passed_count=10,
            failed_count=40,
            pass_rate=0.2,
            confidence_score=0.1,
            recommendation="reject",
            invariant_violations=create_violation_breakdown(
                total_violations=40,
                new_critical_violations=20,
            ),
        )
        rec_reject = service.generate_recommendation(failing_summary)
        assert any(
            "fix" in step.lower()
            or "investigate" in step.lower()
            or "address" in step.lower()
            for step in rec_reject.next_steps
        ), f"Reject next steps should mention fixing: {rec_reject.next_steps}"

        # Test review case
        review_summary = create_evidence_summary(
            passed_count=45,
            failed_count=5,
            pass_rate=0.9,
            confidence_score=0.8,
            recommendation="review",
        )
        rec_review = service.generate_recommendation(review_summary)
        assert any(
            "review" in step.lower()
            or "examine" in step.lower()
            or "check" in step.lower()
            for step in rec_review.next_steps
        ), f"Review next steps should mention review: {rec_review.next_steps}"


# =============================================================================
# Additional Edge Case Tests
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_comparisons_list(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test report generation with empty comparisons list."""
        report = service.generate_json_report(
            sample_evidence_summary,
            comparisons=[],
            include_details=True,
        )

        # Should still generate valid report
        assert "summary" in report
        assert "recommendation" in report
        # Details should not be present when comparisons list is empty
        assert "details" not in report

    def test_summary_without_cost_stats(
        self,
        service: ServiceDecisionReportGenerator,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test report generation when cost_stats is None."""
        summary = create_evidence_summary(cost_stats=None)

        report = service.generate_json_report(summary, sample_comparisons)

        # Should handle None cost_stats gracefully
        assert "summary" in report
        assert "performance" in report
        # Cost section should indicate no data or be None
        performance = report["performance"]
        assert performance.get("cost") is None

    def test_perfect_pass_rate_report(
        self,
        service: ServiceDecisionReportGenerator,
        passing_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test report with 100% pass rate."""
        report = service.generate_json_report(
            passing_evidence_summary,
            sample_comparisons,
        )

        assert report["summary"]["pass_rate"] == 1.0
        assert report["recommendation"]["action"] == "approve"

    def test_zero_pass_rate_report(
        self,
        service: ServiceDecisionReportGenerator,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test report with 0% pass rate."""
        summary = create_evidence_summary(
            passed_count=0,
            failed_count=50,
            pass_rate=0.0,
            confidence_score=0.0,
            recommendation="reject",
            invariant_violations=create_violation_breakdown(
                total_violations=50,
                new_critical_violations=50,
            ),
        )

        report = service.generate_json_report(summary, sample_comparisons)

        assert report["summary"]["pass_rate"] == 0.0
        assert report["recommendation"]["action"] == "reject"


@pytest.mark.unit
class TestServiceInstantiation:
    """Test service creation and configuration."""

    def test_service_creation(self) -> None:
        """Test that service can be instantiated."""
        service = ServiceDecisionReportGenerator()
        assert service is not None

    def test_service_has_required_methods(self) -> None:
        """Test that service has all required methods."""
        service = ServiceDecisionReportGenerator()

        # Check required methods exist
        assert hasattr(service, "generate_cli_report")
        assert hasattr(service, "generate_json_report")
        assert hasattr(service, "generate_markdown_report")
        assert hasattr(service, "generate_recommendation")

        # Check methods are callable
        assert callable(service.generate_cli_report)
        assert callable(service.generate_json_report)
        assert callable(service.generate_markdown_report)
        assert callable(service.generate_recommendation)


__all__ = [
    "TestCLIFormat",
    "TestJSONFormat",
    "TestMarkdownFormat",
    "TestReportStructure",
    "TestRecommendationLogic",
    "TestEdgeCases",
    "TestServiceInstantiation",
]
