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
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_invariant_severity import EnumInvariantSeverity
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.evidence.model_cost_statistics import ModelCostStatistics
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
from omnibase_core.services.service_decision_report_generator import (
    COMPARISON_LIMIT_CLI_VERBOSE,
    COMPARISON_LIMIT_MARKDOWN,
    ServiceDecisionReportGenerator,
)

# =============================================================================
# Helper Functions
# =============================================================================


# Test-specific constants (assumed values for helper functions)
DEFAULT_TEST_EXECUTION_COUNT = (
    10  # Assumed executions for cost per-execution calculations
)


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
        baseline_avg_per_execution=baseline_total / DEFAULT_TEST_EXECUTION_COUNT,
        replay_avg_per_execution=replay_total / DEFAULT_TEST_EXECUTION_COUNT,
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


@pytest.mark.unit
class TestThresholdValidation:
    """Test threshold validation in ServiceDecisionReportGenerator."""

    def test_valid_thresholds_accepted(self) -> None:
        """Test that valid threshold values are accepted."""
        # Should not raise
        service = ServiceDecisionReportGenerator(
            confidence_approve_threshold=0.95,
            confidence_review_threshold=0.75,
            pass_rate_optimal=0.90,
            pass_rate_minimum=0.60,
            latency_blocker_percent=40.0,
            latency_warning_percent=15.0,
            cost_blocker_percent=40.0,
            cost_warning_percent=15.0,
        )
        assert service.confidence_approve_threshold == 0.95

    def test_boundary_thresholds_accepted(self) -> None:
        """Test that boundary values (0.0, 1.0) are accepted for rate thresholds."""
        service = ServiceDecisionReportGenerator(
            confidence_approve_threshold=1.0,
            confidence_review_threshold=0.0,
            pass_rate_optimal=1.0,
            pass_rate_minimum=0.0,
        )
        assert service.confidence_approve_threshold == 1.0
        assert service.confidence_review_threshold == 0.0

    def test_invalid_confidence_approve_threshold_raises(self) -> None:
        """Test that invalid confidence_approve_threshold raises ModelOnexError."""
        with pytest.raises(ModelOnexError, match="confidence_approve_threshold"):
            ServiceDecisionReportGenerator(confidence_approve_threshold=1.5)

        with pytest.raises(ModelOnexError, match="confidence_approve_threshold"):
            ServiceDecisionReportGenerator(confidence_approve_threshold=-0.1)

    def test_invalid_confidence_review_threshold_raises(self) -> None:
        """Test that invalid confidence_review_threshold raises ModelOnexError."""
        with pytest.raises(ModelOnexError, match="confidence_review_threshold"):
            ServiceDecisionReportGenerator(confidence_review_threshold=2.0)

    def test_invalid_pass_rate_thresholds_raise(self) -> None:
        """Test that invalid pass rate thresholds raise ModelOnexError."""
        with pytest.raises(ModelOnexError, match="pass_rate_optimal"):
            ServiceDecisionReportGenerator(pass_rate_optimal=1.1)

        with pytest.raises(ModelOnexError, match="pass_rate_minimum"):
            ServiceDecisionReportGenerator(pass_rate_minimum=-0.5)

    def test_negative_latency_threshold_raises(self) -> None:
        """Test that negative latency thresholds raise ModelOnexError."""
        with pytest.raises(ModelOnexError, match="latency_blocker_percent"):
            ServiceDecisionReportGenerator(latency_blocker_percent=-10.0)

        with pytest.raises(ModelOnexError, match="latency_warning_percent"):
            ServiceDecisionReportGenerator(latency_warning_percent=-5.0)

    def test_negative_cost_threshold_raises(self) -> None:
        """Test that negative cost thresholds raise ModelOnexError."""
        with pytest.raises(ModelOnexError, match="cost_blocker_percent"):
            ServiceDecisionReportGenerator(cost_blocker_percent=-20.0)

        with pytest.raises(ModelOnexError, match="cost_warning_percent"):
            ServiceDecisionReportGenerator(cost_warning_percent=-10.0)

    def test_confidence_threshold_relationship_invalid_raises(self) -> None:
        """Test that approve < review threshold raises ModelOnexError.

        The confidence_approve_threshold must be >= confidence_review_threshold
        because approval requires higher confidence than review.
        """
        with pytest.raises(ModelOnexError, match="confidence_approve_threshold"):
            # approve (0.5) < review (0.8) is invalid
            ServiceDecisionReportGenerator(
                confidence_approve_threshold=0.5,
                confidence_review_threshold=0.8,
            )

    def test_pass_rate_threshold_relationship_invalid_raises(self) -> None:
        """Test that optimal < minimum pass rate raises ModelOnexError.

        The pass_rate_optimal must be >= pass_rate_minimum because the
        optimal target should be at least as high as the minimum.
        """
        with pytest.raises(ModelOnexError, match="pass_rate_optimal"):
            # optimal (0.6) < minimum (0.8) is invalid
            ServiceDecisionReportGenerator(
                pass_rate_optimal=0.6,
                pass_rate_minimum=0.8,
            )

    def test_latency_threshold_relationship_invalid_raises(self) -> None:
        """Test that blocker < warning latency percent raises ModelOnexError.

        The latency_blocker_percent must be >= latency_warning_percent because
        blockers should be triggered at a higher threshold than warnings.
        """
        with pytest.raises(ModelOnexError, match="latency_blocker_percent"):
            # blocker (10.0) < warning (30.0) is invalid
            ServiceDecisionReportGenerator(
                latency_blocker_percent=10.0,
                latency_warning_percent=30.0,
            )

    def test_cost_threshold_relationship_invalid_raises(self) -> None:
        """Test that blocker < warning cost percent raises ModelOnexError.

        The cost_blocker_percent must be >= cost_warning_percent because
        blockers should be triggered at a higher threshold than warnings.
        """
        with pytest.raises(ModelOnexError, match="cost_blocker_percent"):
            # blocker (15.0) < warning (40.0) is invalid
            ServiceDecisionReportGenerator(
                cost_blocker_percent=15.0,
                cost_warning_percent=40.0,
            )

    def test_equal_threshold_relationships_valid(self) -> None:
        """Test that equal blocker/warning thresholds are valid.

        When blocker == warning, both trigger at the same level. This is a
        valid configuration where there's no warning - just direct blocking.
        """
        # All thresholds equal (edge case)
        service = ServiceDecisionReportGenerator(
            confidence_approve_threshold=0.8,
            confidence_review_threshold=0.8,
            pass_rate_optimal=0.9,
            pass_rate_minimum=0.9,
            latency_blocker_percent=30.0,
            latency_warning_percent=30.0,
            cost_blocker_percent=25.0,
            cost_warning_percent=25.0,
        )
        assert service.confidence_approve_threshold == 0.8
        assert service.confidence_review_threshold == 0.8
        assert service.latency_blocker_percent == 30.0
        assert service.latency_warning_percent == 30.0

    def test_validation_error_contains_context(self) -> None:
        """Test that validation errors include context with threshold values."""
        try:
            ServiceDecisionReportGenerator(confidence_approve_threshold=1.5)
        except ModelOnexError as e:
            assert e.context is not None
            # Context is nested under additional_context.context
            inner_context = e.context.get("additional_context", {}).get("context", {})
            assert "threshold" in inner_context
            assert inner_context["threshold"] == 1.5

    def test_relationship_error_contains_both_values_in_context(self) -> None:
        """Test that relationship validation errors include both values in context."""
        try:
            ServiceDecisionReportGenerator(
                confidence_approve_threshold=0.5,
                confidence_review_threshold=0.8,
            )
        except ModelOnexError as e:
            assert e.context is not None
            # Context is nested under additional_context.context
            inner_context = e.context.get("additional_context", {}).get("context", {})
            assert "approve" in inner_context
            assert "review" in inner_context
            assert inner_context["approve"] == 0.5
            assert inner_context["review"] == 0.8


@pytest.mark.unit
class TestEdgeCasesExtended:
    """Extended edge case tests for ServiceDecisionReportGenerator."""

    def test_missing_cost_data_warning_in_recommendation(
        self,
        service: ServiceDecisionReportGenerator,
    ) -> None:
        """Test that missing cost data produces a warning."""
        # Create summary with cost_stats=None
        summary = create_evidence_summary(
            cost_stats=None,
            passed_count=45,
            failed_count=5,
            pass_rate=0.90,
            confidence_score=0.85,
        )

        recommendation = service.generate_recommendation(summary)

        # Verify recommendation.warnings contains cost data incomplete message
        assert any(
            "cost" in warning.lower() and "incomplete" in warning.lower()
            for warning in recommendation.warnings
        ), f"Expected cost incomplete warning in: {recommendation.warnings}"

    def test_long_text_truncation_in_cli(
        self,
        service: ServiceDecisionReportGenerator,
    ) -> None:
        """Test that the _center_text method truncates text longer than REPORT_WIDTH."""
        # Test the internal _center_text method directly for truncation behavior
        long_text = "A" * 100  # 100 characters, well over REPORT_WIDTH (80)
        centered = service._center_text(long_text)

        # Verify truncation: text should be truncated to REPORT_WIDTH (80) with ellipsis
        from omnibase_core.services.service_decision_report_generator import (
            REPORT_WIDTH,
        )

        assert len(centered) == REPORT_WIDTH, (
            f"Centered text should be exactly {REPORT_WIDTH} chars, got {len(centered)}"
        )
        assert centered.endswith("..."), "Truncated text should end with ellipsis"

        # Also test that CLI report handles long corpus_id gracefully (no crash)
        long_corpus_id = "test-corpus-" + "x" * 100
        summary = create_evidence_summary(corpus_id=long_corpus_id)

        # Should not raise - handles long text without crashing
        report = service.generate_cli_report(
            summary,
            comparisons=[],
            verbosity="standard",
        )

        # Verify the report was generated and contains the (possibly long) corpus_id
        assert isinstance(report, str)
        assert len(report) > 0
        # The corpus_id should appear somewhere in the report
        assert "test-corpus-" in report

    def test_center_text_exact_width_not_truncated(
        self,
        service: ServiceDecisionReportGenerator,
    ) -> None:
        """Test that text exactly REPORT_WIDTH chars is NOT truncated."""
        from omnibase_core.services.service_decision_report_generator import (
            REPORT_WIDTH,
        )

        # Create text exactly REPORT_WIDTH characters
        exact_text = "X" * REPORT_WIDTH
        centered = service._center_text(exact_text)

        # Should NOT be truncated (no ellipsis)
        assert len(centered) == REPORT_WIDTH
        assert not centered.endswith("...")
        assert centered == exact_text  # Should be unchanged

    def test_unicode_in_violation_messages(
        self,
        service: ServiceDecisionReportGenerator,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test JSON serialization handles unicode/emoji in violations."""
        # Create violation types with unicode characters
        summary = create_evidence_summary(
            invariant_violations=create_violation_breakdown(
                total_violations=5,
                by_type={
                    "schema_mismatch_\u2713": 2,  # Unicode checkmark
                    "constraint_\u26a0_warning": 3,  # Unicode warning sign
                },
                by_severity={"warning": 5},
                new_violations=3,
            ),
        )

        report = service.generate_json_report(summary, sample_comparisons)

        # Verify JSON report serializes correctly
        json_str = json.dumps(report, default=str, ensure_ascii=False)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Parse back and verify unicode preserved
        parsed = json.loads(json_str)
        assert "\u2713" in str(parsed["violations"]["by_type"])
        assert "\u26a0" in str(parsed["violations"]["by_type"])

    def test_pre_generated_recommendation_reuse(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that pre-generated recommendation is reused across formats."""
        # Generate recommendation once
        recommendation = service.generate_recommendation(sample_evidence_summary)

        # Pass to all three report methods
        cli_report = service.generate_cli_report(
            sample_evidence_summary,
            sample_comparisons,
            verbosity="standard",
            recommendation=recommendation,
        )
        json_report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
            recommendation=recommendation,
        )
        md_report = service.generate_markdown_report(
            sample_evidence_summary,
            sample_comparisons,
            recommendation=recommendation,
        )

        # Verify same recommendation action used in all formats
        assert recommendation.action.upper() in cli_report
        assert json_report["recommendation"]["action"] == recommendation.action
        assert recommendation.action.upper() in md_report

        # Verify same confidence used
        assert json_report["recommendation"]["confidence"] == recommendation.confidence
        assert f"{recommendation.confidence:.0%}" in cli_report

        # Verify same blockers/warnings lists
        assert json_report["recommendation"]["blockers"] == recommendation.blockers
        assert json_report["recommendation"]["warnings"] == recommendation.warnings

    def test_class_constants_used_in_recommendation(
        self,
        service: ServiceDecisionReportGenerator,
    ) -> None:
        """Test that class constants control recommendation thresholds."""
        # Verify thresholds match class constants
        assert service.CONFIDENCE_APPROVE_THRESHOLD == 0.9
        assert service.CONFIDENCE_REVIEW_THRESHOLD == 0.7
        assert service.PASS_RATE_OPTIMAL == 0.95
        assert service.PASS_RATE_MINIMUM == 0.70
        assert service.LATENCY_BLOCKER_PERCENT == 50.0
        assert service.LATENCY_WARNING_PERCENT == 20.0
        assert service.COST_BLOCKER_PERCENT == 50.0
        assert service.COST_WARNING_PERCENT == 20.0

        # Test boundary conditions at threshold values
        # At exactly CONFIDENCE_APPROVE_THRESHOLD with no violations = approve
        approve_summary = create_evidence_summary(
            passed_count=100,
            failed_count=0,
            pass_rate=1.0,
            confidence_score=service.CONFIDENCE_APPROVE_THRESHOLD,  # Exactly 0.9
            invariant_violations=create_violation_breakdown(
                total_violations=0,
                new_critical_violations=0,
            ),
            cost_stats=create_cost_stats(
                baseline_total=10.0,
                replay_total=10.0,  # No cost increase
            ),
        )
        rec = service.generate_recommendation(approve_summary)
        assert rec.action == "approve", (
            f"Expected approve at confidence threshold, got {rec.action}"
        )

        # Just below CONFIDENCE_APPROVE_THRESHOLD = review (not approve)
        review_summary = create_evidence_summary(
            passed_count=100,
            failed_count=0,
            pass_rate=1.0,
            confidence_score=service.CONFIDENCE_APPROVE_THRESHOLD - 0.01,  # 0.89
            invariant_violations=create_violation_breakdown(
                total_violations=0,
                new_critical_violations=0,
            ),
            cost_stats=create_cost_stats(
                baseline_total=10.0,
                replay_total=10.0,
            ),
        )
        rec = service.generate_recommendation(review_summary)
        assert rec.action == "review", (
            f"Expected review below approve threshold, got {rec.action}"
        )

        # At exactly CONFIDENCE_REVIEW_THRESHOLD = review
        at_review_threshold = create_evidence_summary(
            passed_count=100,
            failed_count=0,
            pass_rate=1.0,
            confidence_score=service.CONFIDENCE_REVIEW_THRESHOLD,  # Exactly 0.7
            invariant_violations=create_violation_breakdown(
                total_violations=0,
                new_critical_violations=0,
            ),
            cost_stats=create_cost_stats(
                baseline_total=10.0,
                replay_total=10.0,
            ),
        )
        rec = service.generate_recommendation(at_review_threshold)
        assert rec.action == "review", (
            f"Expected review at review threshold, got {rec.action}"
        )

        # Just below CONFIDENCE_REVIEW_THRESHOLD = reject
        reject_summary = create_evidence_summary(
            passed_count=100,
            failed_count=0,
            pass_rate=1.0,
            confidence_score=service.CONFIDENCE_REVIEW_THRESHOLD - 0.01,  # 0.69
            invariant_violations=create_violation_breakdown(
                total_violations=0,
                new_critical_violations=0,
            ),
            cost_stats=create_cost_stats(
                baseline_total=10.0,
                replay_total=10.0,
            ),
        )
        rec = service.generate_recommendation(reject_summary)
        assert rec.action == "reject", (
            f"Expected reject below review threshold, got {rec.action}"
        )


@pytest.mark.unit
class TestComparisonPagination:
    """Test pagination boundary conditions for comparison display.

    CLI verbose mode displays first 10 comparisons (with "... and N more" message).
    Markdown details displays first 50 comparisons (with "... and N more" message).
    These tests verify boundary conditions at exactly limit, limit+1, and limit-1.
    """

    def test_cli_verbose_exactly_at_limit(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test CLI verbose with exactly LIMIT comparisons shows all without ellipsis."""
        # Create exactly 10 comparisons
        comparisons = [
            create_execution_comparison() for _ in range(COMPARISON_LIMIT_CLI_VERBOSE)
        ]

        report = service.generate_cli_report(
            sample_evidence_summary,
            comparisons,
            verbosity="verbose",
        )

        # Should NOT have "more comparisons" message
        assert "more comparisons" not in report.lower()

    def test_cli_verbose_one_over_limit(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test CLI verbose with LIMIT+1 comparisons shows ellipsis."""
        # Create 11 comparisons
        comparisons = [
            create_execution_comparison()
            for _ in range(COMPARISON_LIMIT_CLI_VERBOSE + 1)
        ]

        report = service.generate_cli_report(
            sample_evidence_summary,
            comparisons,
            verbosity="verbose",
        )

        # Should have "and 1 more comparisons" message
        assert "1 more comparison" in report.lower() or "... and 1 more" in report

    def test_cli_verbose_one_under_limit(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test CLI verbose with LIMIT-1 comparisons shows all without ellipsis."""
        # Create 9 comparisons
        comparisons = [
            create_execution_comparison()
            for _ in range(COMPARISON_LIMIT_CLI_VERBOSE - 1)
        ]

        report = service.generate_cli_report(
            sample_evidence_summary,
            comparisons,
            verbosity="verbose",
        )

        # Should NOT have "more comparisons" message
        assert "more comparisons" not in report.lower()

    def test_markdown_exactly_at_limit(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test Markdown with exactly LIMIT comparisons shows all without ellipsis."""
        # Create exactly 50 comparisons
        comparisons = [
            create_execution_comparison() for _ in range(COMPARISON_LIMIT_MARKDOWN)
        ]

        report = service.generate_markdown_report(
            sample_evidence_summary,
            comparisons,
            include_details=True,
        )

        # Should NOT have "more comparisons" message
        assert "more comparisons" not in report.lower()

    def test_markdown_one_over_limit(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test Markdown with LIMIT+1 comparisons shows ellipsis."""
        # Create 51 comparisons
        comparisons = [
            create_execution_comparison() for _ in range(COMPARISON_LIMIT_MARKDOWN + 1)
        ]

        report = service.generate_markdown_report(
            sample_evidence_summary,
            comparisons,
            include_details=True,
        )

        # Should have "and 1 more comparisons" message
        assert "1 more comparison" in report.lower()

    def test_markdown_one_under_limit(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test Markdown with LIMIT-1 comparisons shows all without ellipsis."""
        # Create 49 comparisons
        comparisons = [
            create_execution_comparison() for _ in range(COMPARISON_LIMIT_MARKDOWN - 1)
        ]

        report = service.generate_markdown_report(
            sample_evidence_summary,
            comparisons,
            include_details=True,
        )

        # Should NOT have "more comparisons" message
        assert "more comparisons" not in report.lower()


@pytest.mark.unit
class TestThresholdBoundary:
    """Test threshold boundary conditions (PR #368 review feedback).

    This class tests edge cases at threshold boundaries:
    - Exact boundary values (0.0, 1.0 for rates; 0.0 for percentages)
    - Values just outside boundaries (-0.001, 1.001)
    - Equal threshold relationships where allowed
    """

    # =========================================================================
    # Rate threshold boundaries (0.0 - 1.0 range)
    # =========================================================================

    def test_threshold_boundary_confidence_approve_zero_valid(self) -> None:
        """Test that 0.0 is a valid confidence_approve_threshold value."""
        # 0.0 is at the lower boundary of the valid range [0.0, 1.0]
        # Must also satisfy: approve >= review, so review must be 0.0
        generator = ServiceDecisionReportGenerator(
            confidence_approve_threshold=0.0,
            confidence_review_threshold=0.0,
        )
        assert generator.confidence_approve_threshold == 0.0
        assert generator is not None

    def test_threshold_boundary_confidence_approve_one_valid(self) -> None:
        """Test that 1.0 is a valid confidence_approve_threshold value."""
        # 1.0 is at the upper boundary of the valid range [0.0, 1.0]
        generator = ServiceDecisionReportGenerator(
            confidence_approve_threshold=1.0,
        )
        assert generator.confidence_approve_threshold == 1.0
        assert generator is not None

    def test_threshold_boundary_confidence_approve_below_zero_invalid(self) -> None:
        """Test that values below 0.0 raise validation error."""
        with pytest.raises(ModelOnexError, match="confidence_approve_threshold"):
            ServiceDecisionReportGenerator(confidence_approve_threshold=-0.001)

    def test_threshold_boundary_confidence_approve_above_one_invalid(self) -> None:
        """Test that values above 1.0 raise validation error."""
        with pytest.raises(ModelOnexError, match="confidence_approve_threshold"):
            ServiceDecisionReportGenerator(confidence_approve_threshold=1.001)

    def test_threshold_boundary_confidence_review_zero_valid(self) -> None:
        """Test that 0.0 is a valid confidence_review_threshold value."""
        generator = ServiceDecisionReportGenerator(
            confidence_review_threshold=0.0,
        )
        assert generator.confidence_review_threshold == 0.0

    def test_threshold_boundary_confidence_review_one_valid(self) -> None:
        """Test that 1.0 is a valid confidence_review_threshold value."""
        # Must also satisfy: approve >= review, so approve must be 1.0
        generator = ServiceDecisionReportGenerator(
            confidence_approve_threshold=1.0,
            confidence_review_threshold=1.0,
        )
        assert generator.confidence_review_threshold == 1.0

    def test_threshold_boundary_confidence_review_below_zero_invalid(self) -> None:
        """Test that values below 0.0 raise validation error."""
        with pytest.raises(ModelOnexError, match="confidence_review_threshold"):
            ServiceDecisionReportGenerator(confidence_review_threshold=-0.001)

    def test_threshold_boundary_confidence_review_above_one_invalid(self) -> None:
        """Test that values above 1.0 raise validation error."""
        with pytest.raises(ModelOnexError, match="confidence_review_threshold"):
            ServiceDecisionReportGenerator(confidence_review_threshold=1.001)

    def test_threshold_boundary_pass_rate_optimal_zero_valid(self) -> None:
        """Test that 0.0 is a valid pass_rate_optimal value."""
        # Must also satisfy: optimal >= minimum, so minimum must be 0.0
        generator = ServiceDecisionReportGenerator(
            pass_rate_optimal=0.0,
            pass_rate_minimum=0.0,
        )
        assert generator.pass_rate_optimal == 0.0

    def test_threshold_boundary_pass_rate_optimal_one_valid(self) -> None:
        """Test that 1.0 is a valid pass_rate_optimal value."""
        generator = ServiceDecisionReportGenerator(
            pass_rate_optimal=1.0,
        )
        assert generator.pass_rate_optimal == 1.0

    def test_threshold_boundary_pass_rate_optimal_below_zero_invalid(self) -> None:
        """Test that values below 0.0 raise validation error."""
        with pytest.raises(ModelOnexError, match="pass_rate_optimal"):
            ServiceDecisionReportGenerator(pass_rate_optimal=-0.001)

    def test_threshold_boundary_pass_rate_optimal_above_one_invalid(self) -> None:
        """Test that values above 1.0 raise validation error."""
        with pytest.raises(ModelOnexError, match="pass_rate_optimal"):
            ServiceDecisionReportGenerator(pass_rate_optimal=1.001)

    def test_threshold_boundary_pass_rate_minimum_zero_valid(self) -> None:
        """Test that 0.0 is a valid pass_rate_minimum value."""
        generator = ServiceDecisionReportGenerator(
            pass_rate_minimum=0.0,
        )
        assert generator.pass_rate_minimum == 0.0

    def test_threshold_boundary_pass_rate_minimum_one_valid(self) -> None:
        """Test that 1.0 is a valid pass_rate_minimum value."""
        # Must also satisfy: optimal >= minimum, so optimal must be 1.0
        generator = ServiceDecisionReportGenerator(
            pass_rate_optimal=1.0,
            pass_rate_minimum=1.0,
        )
        assert generator.pass_rate_minimum == 1.0

    def test_threshold_boundary_pass_rate_minimum_below_zero_invalid(self) -> None:
        """Test that values below 0.0 raise validation error."""
        with pytest.raises(ModelOnexError, match="pass_rate_minimum"):
            ServiceDecisionReportGenerator(pass_rate_minimum=-0.001)

    def test_threshold_boundary_pass_rate_minimum_above_one_invalid(self) -> None:
        """Test that values above 1.0 raise validation error."""
        with pytest.raises(ModelOnexError, match="pass_rate_minimum"):
            ServiceDecisionReportGenerator(pass_rate_minimum=1.001)

    # =========================================================================
    # Percent threshold boundaries (>= 0.0)
    # =========================================================================

    def test_threshold_boundary_latency_blocker_zero_valid(self) -> None:
        """Test that 0.0 is a valid latency_blocker_percent value."""
        # Must also satisfy: blocker >= warning, so warning must be 0.0
        generator = ServiceDecisionReportGenerator(
            latency_blocker_percent=0.0,
            latency_warning_percent=0.0,
        )
        assert generator.latency_blocker_percent == 0.0

    def test_threshold_boundary_latency_blocker_below_zero_invalid(self) -> None:
        """Test that values below 0.0 raise validation error."""
        with pytest.raises(ModelOnexError, match="latency_blocker_percent"):
            ServiceDecisionReportGenerator(latency_blocker_percent=-0.001)

    def test_threshold_boundary_latency_warning_zero_valid(self) -> None:
        """Test that 0.0 is a valid latency_warning_percent value."""
        generator = ServiceDecisionReportGenerator(
            latency_warning_percent=0.0,
        )
        assert generator.latency_warning_percent == 0.0

    def test_threshold_boundary_latency_warning_below_zero_invalid(self) -> None:
        """Test that values below 0.0 raise validation error."""
        with pytest.raises(ModelOnexError, match="latency_warning_percent"):
            ServiceDecisionReportGenerator(latency_warning_percent=-0.001)

    def test_threshold_boundary_cost_blocker_zero_valid(self) -> None:
        """Test that 0.0 is a valid cost_blocker_percent value."""
        # Must also satisfy: blocker >= warning, so warning must be 0.0
        generator = ServiceDecisionReportGenerator(
            cost_blocker_percent=0.0,
            cost_warning_percent=0.0,
        )
        assert generator.cost_blocker_percent == 0.0

    def test_threshold_boundary_cost_blocker_below_zero_invalid(self) -> None:
        """Test that values below 0.0 raise validation error."""
        with pytest.raises(ModelOnexError, match="cost_blocker_percent"):
            ServiceDecisionReportGenerator(cost_blocker_percent=-0.001)

    def test_threshold_boundary_cost_warning_zero_valid(self) -> None:
        """Test that 0.0 is a valid cost_warning_percent value."""
        generator = ServiceDecisionReportGenerator(
            cost_warning_percent=0.0,
        )
        assert generator.cost_warning_percent == 0.0

    def test_threshold_boundary_cost_warning_below_zero_invalid(self) -> None:
        """Test that values below 0.0 raise validation error."""
        with pytest.raises(ModelOnexError, match="cost_warning_percent"):
            ServiceDecisionReportGenerator(cost_warning_percent=-0.001)

    # =========================================================================
    # Equal threshold relationships (edge case where thresholds are equal)
    # =========================================================================

    def test_threshold_boundary_equal_confidence_thresholds_valid(self) -> None:
        """Test that equal approve and review confidence thresholds are valid.

        When confidence_approve_threshold == confidence_review_threshold,
        there's effectively no "review" state - scores either approve or reject.
        """
        generator = ServiceDecisionReportGenerator(
            confidence_approve_threshold=0.85,
            confidence_review_threshold=0.85,
        )
        assert generator.confidence_approve_threshold == 0.85
        assert generator.confidence_review_threshold == 0.85

    def test_threshold_boundary_equal_pass_rate_thresholds_valid(self) -> None:
        """Test that equal optimal and minimum pass rate thresholds are valid.

        When pass_rate_optimal == pass_rate_minimum, there's no "warning" zone -
        pass rates either meet the requirement or trigger a blocker.
        """
        generator = ServiceDecisionReportGenerator(
            pass_rate_optimal=0.9,
            pass_rate_minimum=0.9,
        )
        assert generator.pass_rate_optimal == 0.9
        assert generator.pass_rate_minimum == 0.9

    def test_threshold_boundary_equal_latency_thresholds_valid(self) -> None:
        """Test that equal blocker and warning latency thresholds are valid.

        When latency_blocker_percent == latency_warning_percent, there's no
        "warning" zone - latency regressions either pass or block.
        """
        generator = ServiceDecisionReportGenerator(
            latency_blocker_percent=25.0,
            latency_warning_percent=25.0,
        )
        assert generator.latency_blocker_percent == 25.0
        assert generator.latency_warning_percent == 25.0

    def test_threshold_boundary_equal_cost_thresholds_valid(self) -> None:
        """Test that equal blocker and warning cost thresholds are valid.

        When cost_blocker_percent == cost_warning_percent, there's no
        "warning" zone - cost increases either pass or block.
        """
        generator = ServiceDecisionReportGenerator(
            cost_blocker_percent=30.0,
            cost_warning_percent=30.0,
        )
        assert generator.cost_blocker_percent == 30.0
        assert generator.cost_warning_percent == 30.0

    def test_threshold_boundary_all_equal_at_zero_valid(self) -> None:
        """Test extreme case: all rate thresholds at 0.0 and all percent at 0.0.

        This is a valid (if strict) configuration where any deviation from
        perfection triggers blockers.
        """
        generator = ServiceDecisionReportGenerator(
            confidence_approve_threshold=0.0,
            confidence_review_threshold=0.0,
            pass_rate_optimal=0.0,
            pass_rate_minimum=0.0,
            latency_blocker_percent=0.0,
            latency_warning_percent=0.0,
            cost_blocker_percent=0.0,
            cost_warning_percent=0.0,
        )
        assert generator.confidence_approve_threshold == 0.0
        assert generator.latency_blocker_percent == 0.0

    def test_threshold_boundary_all_rate_thresholds_at_one_valid(self) -> None:
        """Test extreme case: all rate thresholds at 1.0.

        This configuration requires perfect confidence and pass rate for approval.
        """
        generator = ServiceDecisionReportGenerator(
            confidence_approve_threshold=1.0,
            confidence_review_threshold=1.0,
            pass_rate_optimal=1.0,
            pass_rate_minimum=1.0,
        )
        assert generator.confidence_approve_threshold == 1.0
        assert generator.pass_rate_optimal == 1.0

    # =========================================================================
    # Relationship boundary violations (edge cases just violating relationships)
    # =========================================================================

    def test_threshold_boundary_approve_just_below_review_invalid(self) -> None:
        """Test that approve just below review (by epsilon) raises error.

        The constraint is: approve >= review. Testing with values that differ
        by a tiny amount (0.001) to catch off-by-one errors in comparison.
        """
        with pytest.raises(ModelOnexError, match="confidence_approve_threshold"):
            ServiceDecisionReportGenerator(
                confidence_approve_threshold=0.799,
                confidence_review_threshold=0.800,
            )

    def test_threshold_boundary_optimal_just_below_minimum_invalid(self) -> None:
        """Test that optimal just below minimum (by epsilon) raises error.

        The constraint is: optimal >= minimum. Testing with values that differ
        by a tiny amount (0.001).
        """
        with pytest.raises(ModelOnexError, match="pass_rate_optimal"):
            ServiceDecisionReportGenerator(
                pass_rate_optimal=0.899,
                pass_rate_minimum=0.900,
            )

    def test_threshold_boundary_latency_blocker_just_below_warning_invalid(
        self,
    ) -> None:
        """Test that latency blocker just below warning raises error.

        The constraint is: blocker >= warning.
        """
        with pytest.raises(ModelOnexError, match="latency_blocker_percent"):
            ServiceDecisionReportGenerator(
                latency_blocker_percent=19.999,
                latency_warning_percent=20.000,
            )

    def test_threshold_boundary_cost_blocker_just_below_warning_invalid(self) -> None:
        """Test that cost blocker just below warning raises error.

        The constraint is: blocker >= warning.
        """
        with pytest.raises(ModelOnexError, match="cost_blocker_percent"):
            ServiceDecisionReportGenerator(
                cost_blocker_percent=19.999,
                cost_warning_percent=20.000,
            )


# =============================================================================
# JSON Round-Trip Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestJSONRoundTrip:
    """Test JSON serialization round-trip preserves all data.

    These tests verify that generating a JSON report, serializing it to a string,
    and parsing it back preserves all data without loss. This is critical for:
    - API responses that get deserialized by clients
    - Storage and retrieval from databases/files
    - Cross-service communication where reports are serialized/deserialized
    """

    def test_json_round_trip_preserves_summary_data(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that Summary -> JSON -> dict preserves all summary data."""
        from datetime import UTC, datetime

        # Use fixed timestamp for deterministic output
        fixed_timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        # Generate JSON report
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
            include_details=True,
            generated_at=fixed_timestamp,
        )

        # Serialize to JSON string and parse back
        json_str = json.dumps(report, default=str)
        roundtrip_data = json.loads(json_str)

        # Verify summary section data preserved
        summary = roundtrip_data["summary"]
        assert summary["corpus_id"] == sample_evidence_summary.corpus_id
        assert summary["baseline_version"] == sample_evidence_summary.baseline_version
        assert summary["replay_version"] == sample_evidence_summary.replay_version
        assert summary["total_executions"] == sample_evidence_summary.total_executions
        assert summary["passed_count"] == sample_evidence_summary.passed_count
        assert summary["failed_count"] == sample_evidence_summary.failed_count
        assert summary["pass_rate"] == sample_evidence_summary.pass_rate
        assert summary["confidence_score"] == sample_evidence_summary.confidence_score
        assert summary["headline"] == sample_evidence_summary.headline

    def test_json_round_trip_preserves_numeric_precision(
        self,
        service: ServiceDecisionReportGenerator,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that numeric values with decimal precision are preserved."""
        # Create summary with precise decimal values
        precise_latency = create_latency_stats(
            baseline_avg_ms=123.456789,
            replay_avg_ms=98.7654321,
            baseline_p50_ms=100.111,
            replay_p50_ms=90.222,
            baseline_p95_ms=200.333,
            replay_p95_ms=180.444,
        )
        precise_cost = create_cost_stats(
            baseline_total=10.123456,
            replay_total=8.654321,
        )
        summary = create_evidence_summary(
            latency_stats=precise_latency,
            cost_stats=precise_cost,
            pass_rate=0.947368421,  # Precise decimal
            confidence_score=0.876543,
        )

        # Generate and round-trip
        report = service.generate_json_report(summary, sample_comparisons)
        json_str = json.dumps(report, default=str)
        roundtrip_data = json.loads(json_str)

        # Verify numeric precision preserved (JSON floats)
        latency = roundtrip_data["performance"]["latency"]
        assert latency["baseline_avg_ms"] == 123.456789
        assert latency["replay_avg_ms"] == 98.7654321
        assert latency["baseline_p50_ms"] == 100.111
        assert latency["replay_p50_ms"] == 90.222
        assert latency["baseline_p95_ms"] == 200.333
        assert latency["replay_p95_ms"] == 180.444

        cost = roundtrip_data["performance"]["cost"]
        assert cost["baseline_total"] == 10.123456
        assert cost["replay_total"] == 8.654321

        # Verify summary precision
        assert roundtrip_data["summary"]["pass_rate"] == 0.947368421
        assert roundtrip_data["summary"]["confidence_score"] == 0.876543

    def test_json_round_trip_preserves_nested_structures(
        self,
        service: ServiceDecisionReportGenerator,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that nested objects (violations, performance) are preserved."""
        # Create summary with detailed nested structures
        violations = create_violation_breakdown(
            total_violations=15,
            by_type={
                "output_equivalence": 5,
                "schema_mismatch": 4,
                "latency_threshold": 3,
                "cost_threshold": 2,
                "custom_invariant": 1,
            },
            by_severity={
                "critical": 3,
                "warning": 7,
                "info": 5,
            },
            new_violations=8,
            new_critical_violations=2,
            fixed_violations=4,
        )
        summary = create_evidence_summary(
            invariant_violations=violations,
            passed_count=35,
            failed_count=15,
            pass_rate=0.70,
            confidence_score=0.65,
            recommendation="review",
        )

        # Generate and round-trip
        report = service.generate_json_report(summary, sample_comparisons)
        json_str = json.dumps(report, default=str)
        roundtrip_data = json.loads(json_str)

        # Verify violations nested structure
        v = roundtrip_data["violations"]
        assert v["total"] == 15
        assert v["new_violations"] == 8
        assert v["new_critical_violations"] == 2
        assert v["fixed_violations"] == 4

        # Verify by_type dict preserved
        assert v["by_type"]["output_equivalence"] == 5
        assert v["by_type"]["schema_mismatch"] == 4
        assert v["by_type"]["latency_threshold"] == 3
        assert v["by_type"]["cost_threshold"] == 2
        assert v["by_type"]["custom_invariant"] == 1
        assert len(v["by_type"]) == 5

        # Verify by_severity dict preserved
        assert v["by_severity"]["critical"] == 3
        assert v["by_severity"]["warning"] == 7
        assert v["by_severity"]["info"] == 5
        assert len(v["by_severity"]) == 3

    def test_json_round_trip_preserves_lists(
        self,
        service: ServiceDecisionReportGenerator,
        failing_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that list fields (blockers, warnings, next_steps) are preserved."""
        # Generate and round-trip (failing summary has blockers)
        report = service.generate_json_report(
            failing_evidence_summary,
            sample_comparisons,
        )
        json_str = json.dumps(report, default=str)
        roundtrip_data = json.loads(json_str)

        # Verify recommendation lists
        rec = roundtrip_data["recommendation"]

        # Blockers should be a non-empty list
        assert isinstance(rec["blockers"], list)
        assert len(rec["blockers"]) > 0
        for blocker in rec["blockers"]:
            assert isinstance(blocker, str)
            assert len(blocker) > 0

        # Warnings should be a list (may be empty or non-empty)
        assert isinstance(rec["warnings"], list)

        # Next steps should be a non-empty list
        assert isinstance(rec["next_steps"], list)
        assert len(rec["next_steps"]) > 0
        for step in rec["next_steps"]:
            assert isinstance(step, str)
            assert len(step) > 0

    def test_json_round_trip_preserves_optional_cost_stats_none(
        self,
        service: ServiceDecisionReportGenerator,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that None cost_stats is preserved as null in JSON."""
        # Create summary without cost stats
        summary = create_evidence_summary(cost_stats=None)

        # Generate and round-trip
        report = service.generate_json_report(summary, sample_comparisons)
        json_str = json.dumps(report, default=str)
        roundtrip_data = json.loads(json_str)

        # Verify cost is null (None in Python)
        assert roundtrip_data["performance"]["cost"] is None

    def test_json_round_trip_preserves_optional_cost_stats_present(
        self,
        service: ServiceDecisionReportGenerator,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that present cost_stats is preserved with all fields."""
        # Create summary with cost stats
        cost_stats = create_cost_stats(
            baseline_total=100.50,
            replay_total=75.25,
        )
        summary = create_evidence_summary(cost_stats=cost_stats)

        # Generate and round-trip
        report = service.generate_json_report(summary, sample_comparisons)
        json_str = json.dumps(report, default=str)
        roundtrip_data = json.loads(json_str)

        # Verify cost data present and correct
        cost = roundtrip_data["performance"]["cost"]
        assert cost is not None
        assert cost["baseline_total"] == 100.50
        assert cost["replay_total"] == 75.25
        assert cost["delta_total"] == cost_stats.delta_total
        assert cost["delta_percent"] == cost_stats.delta_percent
        assert (
            cost["baseline_avg_per_execution"] == cost_stats.baseline_avg_per_execution
        )
        assert cost["replay_avg_per_execution"] == cost_stats.replay_avg_per_execution

    def test_json_round_trip_preserves_details_when_included(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that comparison details are preserved when include_details=True."""
        # Generate with details
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
            include_details=True,
        )
        json_str = json.dumps(report, default=str)
        roundtrip_data = json.loads(json_str)

        # Verify details present and correct length
        assert "details" in roundtrip_data
        details = roundtrip_data["details"]
        assert isinstance(details, list)
        assert len(details) == len(sample_comparisons)

        # Verify each detail has required fields
        for detail in details:
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
            assert "compared_at" in detail

            # Verify boolean fields are actual booleans
            assert isinstance(detail["input_hash_match"], bool)
            assert isinstance(detail["output_match"], bool)

            # Verify numeric fields are numbers
            assert isinstance(detail["baseline_latency_ms"], (int, float))
            assert isinstance(detail["replay_latency_ms"], (int, float))
            assert isinstance(detail["latency_delta_ms"], (int, float))
            assert isinstance(detail["latency_delta_percent"], (int, float))

    def test_json_round_trip_preserves_recommendation_fields(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that all recommendation fields are preserved."""
        # Pre-generate recommendation for comparison
        original_rec = service.generate_recommendation(sample_evidence_summary)

        # Generate report with same recommendation
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
            recommendation=original_rec,
        )
        json_str = json.dumps(report, default=str)
        roundtrip_data = json.loads(json_str)

        # Verify recommendation fields match
        rec = roundtrip_data["recommendation"]
        assert rec["action"] == original_rec.action
        assert rec["confidence"] == original_rec.confidence
        assert rec["rationale"] == original_rec.rationale
        assert rec["blockers"] == original_rec.blockers
        assert rec["warnings"] == original_rec.warnings
        assert rec["next_steps"] == original_rec.next_steps

    def test_json_round_trip_with_unicode_content(
        self,
        service: ServiceDecisionReportGenerator,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test that unicode characters in content are preserved."""
        # Create summary with unicode in violation types
        violations = create_violation_breakdown(
            total_violations=3,
            by_type={
                "schema_\u2713_valid": 1,  # Unicode checkmark
                "constraint_\u26a0": 1,  # Unicode warning
                "test_\u2764_heart": 1,  # Unicode heart
            },
            by_severity={"warning": 3},
            new_violations=2,
        )
        summary = create_evidence_summary(invariant_violations=violations)

        # Generate and round-trip (ensure_ascii=False to preserve unicode)
        report = service.generate_json_report(summary, sample_comparisons)
        json_str = json.dumps(report, default=str, ensure_ascii=False)
        roundtrip_data = json.loads(json_str)

        # Verify unicode preserved
        by_type = roundtrip_data["violations"]["by_type"]
        assert "schema_\u2713_valid" in by_type
        assert "constraint_\u26a0" in by_type
        assert "test_\u2764_heart" in by_type

    def test_json_round_trip_comprehensive_data_integrity(
        self,
        service: ServiceDecisionReportGenerator,
    ) -> None:
        """Comprehensive test verifying complete data integrity through round-trip.

        This test creates a fully-populated ModelEvidenceSummary with all optional
        fields, generates JSON, serializes to string, parses back, and verifies
        every field matches the original input data.
        """
        from datetime import UTC, datetime

        # Create comprehensive test data with all fields populated
        latency_stats = create_latency_stats(
            baseline_avg_ms=150.5,
            replay_avg_ms=125.3,
            baseline_p50_ms=140.0,
            replay_p50_ms=115.0,
            baseline_p95_ms=250.0,
            replay_p95_ms=200.0,
        )
        cost_stats = create_cost_stats(
            baseline_total=50.0,
            replay_total=35.0,
        )
        violations = create_violation_breakdown(
            total_violations=10,
            by_type={"output": 5, "schema": 3, "latency": 2},
            by_severity={"critical": 2, "warning": 5, "info": 3},
            new_violations=6,
            new_critical_violations=1,
            fixed_violations=3,
        )

        # Create evidence summary with all fields
        summary = create_evidence_summary(
            corpus_id="comprehensive-test-corpus-001",
            baseline_version="v2.0.0",
            replay_version="v2.1.0-rc1",
            total_executions=100,
            passed_count=90,
            failed_count=10,
            pass_rate=0.90,
            confidence_score=0.85,
            recommendation="review",
            latency_stats=latency_stats,
            cost_stats=cost_stats,
            invariant_violations=violations,
        )

        # Create comparisons with varied data
        comparisons = [
            create_execution_comparison(
                output_match=True,
                baseline_passed=True,
                replay_passed=True,
                baseline_latency_ms=100.0 + i * 10,
                replay_latency_ms=90.0 + i * 8,
                baseline_cost=0.01 + i * 0.001,
                replay_cost=0.008 + i * 0.0008,
            )
            for i in range(5)
        ]
        # Add some failing comparisons
        comparisons.extend(
            [
                create_execution_comparison(
                    output_match=False,
                    baseline_passed=True,
                    replay_passed=False,
                    baseline_latency_ms=150.0,
                    replay_latency_ms=300.0,
                )
                for _ in range(2)
            ]
        )

        # Use fixed timestamp for determinism
        fixed_timestamp = datetime(2025, 6, 15, 14, 30, 0, tzinfo=UTC)

        # Generate JSON report with all details
        report = service.generate_json_report(
            summary,
            comparisons,
            include_details=True,
            generated_at=fixed_timestamp,
        )

        # Serialize and deserialize
        json_str = json.dumps(report, default=str, indent=2)
        roundtrip_data = json.loads(json_str)

        # ===== VERIFY ALL DATA PRESERVED =====

        # 1. Metadata
        assert roundtrip_data["report_version"] == "1.0.0"
        assert roundtrip_data["generated_at"] == "2025-06-15T14:30:00+00:00"

        # 2. Summary section
        s = roundtrip_data["summary"]
        assert s["corpus_id"] == "comprehensive-test-corpus-001"
        assert s["baseline_version"] == "v2.0.0"
        assert s["replay_version"] == "v2.1.0-rc1"
        assert s["total_executions"] == 100
        assert s["passed_count"] == 90
        assert s["failed_count"] == 10
        assert s["pass_rate"] == 0.90
        assert s["confidence_score"] == 0.85

        # 3. Violations section
        v = roundtrip_data["violations"]
        assert v["total"] == 10
        assert v["new_violations"] == 6
        assert v["new_critical_violations"] == 1
        assert v["fixed_violations"] == 3
        assert v["by_type"] == {"output": 5, "schema": 3, "latency": 2}
        assert v["by_severity"] == {"critical": 2, "warning": 5, "info": 3}

        # 4. Performance - Latency
        lat = roundtrip_data["performance"]["latency"]
        assert lat["baseline_avg_ms"] == 150.5
        assert lat["replay_avg_ms"] == 125.3
        assert lat["baseline_p50_ms"] == 140.0
        assert lat["replay_p50_ms"] == 115.0
        assert lat["baseline_p95_ms"] == 250.0
        assert lat["replay_p95_ms"] == 200.0
        # Verify computed deltas (from helper function)
        assert lat["delta_avg_ms"] == 125.3 - 150.5  # -25.2
        # Delta percent calculation: (125.3 - 150.5) / 150.5 * 100 = -16.744...
        assert abs(lat["delta_avg_percent"] - (-16.744186046511628)) < 0.0001

        # 5. Performance - Cost
        cost = roundtrip_data["performance"]["cost"]
        assert cost["baseline_total"] == 50.0
        assert cost["replay_total"] == 35.0
        assert cost["delta_total"] == -15.0
        assert cost["delta_percent"] == -30.0

        # 6. Recommendation section
        rec = roundtrip_data["recommendation"]
        assert rec["action"] in ("approve", "review", "reject")
        assert isinstance(rec["confidence"], float)
        assert isinstance(rec["rationale"], str)
        assert isinstance(rec["blockers"], list)
        assert isinstance(rec["warnings"], list)
        assert isinstance(rec["next_steps"], list)

        # 7. Details section
        assert "details" in roundtrip_data
        assert len(roundtrip_data["details"]) == 7  # 5 passing + 2 failing

        # Verify first comparison detail
        first_detail = roundtrip_data["details"][0]
        assert first_detail["output_match"] is True
        assert first_detail["input_hash_match"] is True
        assert first_detail["baseline_latency_ms"] == 100.0
        assert first_detail["replay_latency_ms"] == 90.0

        # Verify a failing comparison detail
        failing_detail = roundtrip_data["details"][5]
        assert failing_detail["output_match"] is False
        assert failing_detail["baseline_latency_ms"] == 150.0
        assert failing_detail["replay_latency_ms"] == 300.0


# =============================================================================
# JSON Schema Validation Tests (TypedDict Compliance)
# =============================================================================


@pytest.mark.unit
class TestJSONSchemaValidation:
    """Test JSON output validates against TypedDict schema structures.

    These tests verify that the JSON output from generate_json_report()
    conforms to the TypedDict structures defined in the types module:
    - TypedDictDecisionReport (top-level)
    - TypedDictDecisionReportSummary
    - TypedDictDecisionReportViolations
    - TypedDictDecisionReportPerformance
    - TypedDictDecisionReportLatency
    - TypedDictDecisionReportCost
    - TypedDictDecisionReportRecommendation
    - TypedDictDecisionReportDetail
    """

    def test_json_output_matches_typed_dict_schema(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Verify JSON output conforms to TypedDictDecisionReport structure."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
            include_details=True,
        )

        # Verify top-level required keys exist (TypedDictDecisionReport)
        top_level_required_keys = {
            "report_version",
            "generated_at",
            "summary",
            "violations",
            "performance",
            "recommendation",
        }
        assert top_level_required_keys.issubset(report.keys()), (
            f"Missing top-level keys: {top_level_required_keys - report.keys()}"
        )

    def test_json_schema_summary_section_keys(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test summary section has all required TypedDictDecisionReportSummary keys."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        summary_required_keys = {
            "summary_id",
            "corpus_id",
            "baseline_version",
            "replay_version",
            "total_executions",
            "passed_count",
            "failed_count",
            "pass_rate",
            "confidence_score",
            "headline",
            "started_at",
            "ended_at",
        }

        summary = report["summary"]
        assert summary_required_keys.issubset(summary.keys()), (
            f"Missing summary keys: {summary_required_keys - summary.keys()}"
        )

    def test_json_schema_summary_section_types(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test summary section value types match TypedDictDecisionReportSummary."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        summary = report["summary"]

        # String fields
        assert isinstance(summary["summary_id"], str)
        assert isinstance(summary["corpus_id"], str)
        assert isinstance(summary["baseline_version"], str)
        assert isinstance(summary["replay_version"], str)
        assert isinstance(summary["headline"], str)
        assert isinstance(summary["started_at"], str)
        assert isinstance(summary["ended_at"], str)

        # Integer fields
        assert isinstance(summary["total_executions"], int)
        assert isinstance(summary["passed_count"], int)
        assert isinstance(summary["failed_count"], int)

        # Float fields
        assert isinstance(summary["pass_rate"], float)
        assert isinstance(summary["confidence_score"], float)

    def test_json_schema_violations_section_keys(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test violations section has all TypedDictDecisionReportViolations keys."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        violations_required_keys = {
            "total",
            "by_type",
            "by_severity",
            "new_violations",
            "new_critical_violations",
            "fixed_violations",
        }

        violations = report["violations"]
        assert violations_required_keys.issubset(violations.keys()), (
            f"Missing violations keys: {violations_required_keys - violations.keys()}"
        )

    def test_json_schema_violations_section_types(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test violations section value types match TypedDictDecisionReportViolations."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        violations = report["violations"]

        # Integer fields
        assert isinstance(violations["total"], int)
        assert isinstance(violations["new_violations"], int)
        assert isinstance(violations["new_critical_violations"], int)
        assert isinstance(violations["fixed_violations"], int)

        # Dict[str, int] fields
        assert isinstance(violations["by_type"], dict)
        assert isinstance(violations["by_severity"], dict)
        for key, value in violations["by_type"].items():
            assert isinstance(key, str), f"by_type key {key} is not a string"
            assert isinstance(value, int), f"by_type[{key}] value {value} is not an int"
        for key, value in violations["by_severity"].items():
            assert isinstance(key, str), f"by_severity key {key} is not a string"
            assert isinstance(value, int), (
                f"by_severity[{key}] value {value} is not an int"
            )

    def test_json_schema_performance_latency_keys(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test performance.latency has all TypedDictDecisionReportLatency keys."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        latency_required_keys = {
            "baseline_avg_ms",
            "replay_avg_ms",
            "delta_avg_ms",
            "delta_avg_percent",
            "baseline_p50_ms",
            "replay_p50_ms",
            "delta_p50_percent",
            "baseline_p95_ms",
            "replay_p95_ms",
            "delta_p95_percent",
        }

        performance = report["performance"]
        assert "latency" in performance
        latency = performance["latency"]
        assert latency_required_keys.issubset(latency.keys()), (
            f"Missing latency keys: {latency_required_keys - latency.keys()}"
        )

    def test_json_schema_performance_latency_types(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test performance.latency value types match TypedDictDecisionReportLatency."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        latency = report["performance"]["latency"]

        # All latency fields are floats
        float_fields = [
            "baseline_avg_ms",
            "replay_avg_ms",
            "delta_avg_ms",
            "delta_avg_percent",
            "baseline_p50_ms",
            "replay_p50_ms",
            "delta_p50_percent",
            "baseline_p95_ms",
            "replay_p95_ms",
            "delta_p95_percent",
        ]

        for field in float_fields:
            assert isinstance(latency[field], (int, float)), (
                f"latency[{field}] should be float, got {type(latency[field])}"
            )

    def test_json_schema_performance_cost_keys_when_present(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test performance.cost has all TypedDictDecisionReportCost keys when present."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        cost_required_keys = {
            "baseline_total",
            "replay_total",
            "delta_total",
            "delta_percent",
            "baseline_avg_per_execution",
            "replay_avg_per_execution",
        }

        performance = report["performance"]
        cost = performance["cost"]

        if cost is not None:
            assert cost_required_keys.issubset(cost.keys()), (
                f"Missing cost keys: {cost_required_keys - cost.keys()}"
            )

    def test_json_schema_performance_cost_types_when_present(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test performance.cost value types match TypedDictDecisionReportCost."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        cost = report["performance"]["cost"]

        if cost is not None:
            # All cost fields are floats
            float_fields = [
                "baseline_total",
                "replay_total",
                "delta_total",
                "delta_percent",
                "baseline_avg_per_execution",
                "replay_avg_per_execution",
            ]

            for field in float_fields:
                assert isinstance(cost[field], (int, float)), (
                    f"cost[{field}] should be float, got {type(cost[field])}"
                )

    def test_json_schema_performance_cost_null_when_missing(
        self,
        service: ServiceDecisionReportGenerator,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test performance.cost is None when cost_stats not provided."""
        summary = create_evidence_summary(cost_stats=None)

        report = service.generate_json_report(summary, sample_comparisons)

        # Cost should be None per TypedDictDecisionReportPerformance
        assert report["performance"]["cost"] is None

    def test_json_schema_recommendation_section_keys(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test recommendation has all TypedDictDecisionReportRecommendation keys."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        recommendation_required_keys = {
            "action",
            "confidence",
            "blockers",
            "warnings",
            "next_steps",
            "rationale",
        }

        recommendation = report["recommendation"]
        assert recommendation_required_keys.issubset(recommendation.keys()), (
            f"Missing recommendation keys: "
            f"{recommendation_required_keys - recommendation.keys()}"
        )

    def test_json_schema_recommendation_section_types(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test recommendation value types match TypedDictDecisionReportRecommendation."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        recommendation = report["recommendation"]

        # action is Literal["approve", "review", "reject"]
        assert isinstance(recommendation["action"], str)
        assert recommendation["action"] in ("approve", "review", "reject"), (
            f"Invalid action: {recommendation['action']}"
        )

        # confidence is float
        assert isinstance(recommendation["confidence"], (int, float))

        # rationale is str
        assert isinstance(recommendation["rationale"], str)

        # blockers, warnings, next_steps are list[str]
        assert isinstance(recommendation["blockers"], list)
        assert isinstance(recommendation["warnings"], list)
        assert isinstance(recommendation["next_steps"], list)

        for blocker in recommendation["blockers"]:
            assert isinstance(blocker, str), f"Blocker should be str: {blocker}"
        for warning in recommendation["warnings"]:
            assert isinstance(warning, str), f"Warning should be str: {warning}"
        for step in recommendation["next_steps"]:
            assert isinstance(step, str), f"Next step should be str: {step}"

    def test_json_schema_details_not_present_by_default(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test details key is NotRequired - absent when include_details=False."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
            include_details=False,
        )

        # details is NotRequired - should not be present
        assert "details" not in report

    def test_json_schema_details_section_keys_when_present(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test details items have all TypedDictDecisionReportDetail keys."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
            include_details=True,
        )

        detail_required_keys = {
            "comparison_id",
            "baseline_execution_id",
            "replay_execution_id",
            "input_hash",
            "input_hash_match",
            "output_match",
            "baseline_latency_ms",
            "replay_latency_ms",
            "latency_delta_ms",
            "latency_delta_percent",
            "baseline_cost",
            "replay_cost",
            "cost_delta",
            "cost_delta_percent",
            "compared_at",
        }

        assert "details" in report
        assert isinstance(report["details"], list)
        assert len(report["details"]) > 0, "Expected at least one detail item"

        for i, detail in enumerate(report["details"]):
            assert detail_required_keys.issubset(detail.keys()), (
                f"Detail item {i} missing keys: {detail_required_keys - detail.keys()}"
            )

    def test_json_schema_details_section_types(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test details items value types match TypedDictDecisionReportDetail."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
            include_details=True,
        )

        for i, detail in enumerate(report["details"]):
            # String fields
            assert isinstance(detail["comparison_id"], str), (
                f"Detail {i}: comparison_id"
            )
            assert isinstance(detail["baseline_execution_id"], str), (
                f"Detail {i}: baseline_execution_id"
            )
            assert isinstance(detail["replay_execution_id"], str), (
                f"Detail {i}: replay_execution_id"
            )
            assert isinstance(detail["input_hash"], str), f"Detail {i}: input_hash"
            assert isinstance(detail["compared_at"], str), f"Detail {i}: compared_at"

            # Boolean fields
            assert isinstance(detail["input_hash_match"], bool), (
                f"Detail {i}: input_hash_match"
            )
            assert isinstance(detail["output_match"], bool), f"Detail {i}: output_match"

            # Float fields (always present)
            assert isinstance(detail["baseline_latency_ms"], (int, float)), (
                f"Detail {i}: baseline_latency_ms"
            )
            assert isinstance(detail["replay_latency_ms"], (int, float)), (
                f"Detail {i}: replay_latency_ms"
            )
            assert isinstance(detail["latency_delta_ms"], (int, float)), (
                f"Detail {i}: latency_delta_ms"
            )
            assert isinstance(detail["latency_delta_percent"], (int, float)), (
                f"Detail {i}: latency_delta_percent"
            )

            # Nullable float fields (float | None)
            baseline_cost = detail["baseline_cost"]
            replay_cost = detail["replay_cost"]
            cost_delta = detail["cost_delta"]
            cost_delta_percent = detail["cost_delta_percent"]

            assert baseline_cost is None or isinstance(baseline_cost, (int, float)), (
                f"Detail {i}: baseline_cost should be float | None"
            )
            assert replay_cost is None or isinstance(replay_cost, (int, float)), (
                f"Detail {i}: replay_cost should be float | None"
            )
            assert cost_delta is None or isinstance(cost_delta, (int, float)), (
                f"Detail {i}: cost_delta should be float | None"
            )
            assert cost_delta_percent is None or isinstance(
                cost_delta_percent, (int, float)
            ), f"Detail {i}: cost_delta_percent should be float | None"

    def test_json_schema_top_level_types(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test top-level field types match TypedDictDecisionReport."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
        )

        # report_version is str
        assert isinstance(report["report_version"], str)

        # generated_at is str (ISO timestamp)
        assert isinstance(report["generated_at"], str)

        # Nested structures are dicts
        assert isinstance(report["summary"], dict)
        assert isinstance(report["violations"], dict)
        assert isinstance(report["performance"], dict)
        assert isinstance(report["recommendation"], dict)

    def test_json_schema_empty_comparisons_no_details(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test schema compliance when comparisons list is empty."""
        report = service.generate_json_report(
            sample_evidence_summary,
            comparisons=[],
            include_details=True,
        )

        # Even with include_details=True, empty comparisons = no details key
        assert "details" not in report

        # All other required sections should still be present and valid
        assert "report_version" in report
        assert "generated_at" in report
        assert "summary" in report
        assert "violations" in report
        assert "performance" in report
        assert "recommendation" in report

    def test_json_schema_empty_violations(
        self,
        service: ServiceDecisionReportGenerator,
        passing_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test schema compliance with zero violations."""
        report = service.generate_json_report(
            passing_evidence_summary,
            sample_comparisons,
        )

        violations = report["violations"]

        # Should have correct structure even with empty dicts
        assert violations["total"] == 0
        assert isinstance(violations["by_type"], dict)
        assert isinstance(violations["by_severity"], dict)
        assert len(violations["by_type"]) == 0
        assert len(violations["by_severity"]) == 0

    def test_json_schema_all_action_types(
        self,
        service: ServiceDecisionReportGenerator,
        passing_evidence_summary: ModelEvidenceSummary,
        mixed_evidence_summary: ModelEvidenceSummary,
        failing_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test schema compliance for all recommendation action types."""
        # Test each action type
        summaries = [
            passing_evidence_summary,  # Should produce "approve"
            mixed_evidence_summary,  # Should produce "review"
            failing_evidence_summary,  # Should produce "reject"
        ]

        expected_actions = {"approve", "review", "reject"}
        actual_actions = set()

        for summary in summaries:
            report = service.generate_json_report(summary, sample_comparisons)
            action = report["recommendation"]["action"]
            actual_actions.add(action)

            # Each action should be valid per Literal type
            assert action in expected_actions, f"Invalid action: {action}"

        # We should cover all three action types across our test summaries
        # (This also validates our test fixtures produce diverse outputs)
        assert len(actual_actions) == 3, (
            f"Test fixtures should cover all action types, got: {actual_actions}"
        )

    def test_json_schema_iso_timestamp_format(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test timestamp strings are valid ISO 8601 format."""
        report = service.generate_json_report(
            sample_evidence_summary,
            sample_comparisons,
            include_details=True,
        )

        # Test top-level generated_at
        generated_at = report["generated_at"]
        try:
            # ISO format with timezone
            datetime.fromisoformat(generated_at)
        except ValueError:
            pytest.fail(f"generated_at is not valid ISO format: {generated_at}")

        # Test summary timestamps
        summary = report["summary"]
        for field in ["started_at", "ended_at"]:
            timestamp = summary[field]
            try:
                datetime.fromisoformat(timestamp)
            except ValueError:
                pytest.fail(f"summary.{field} is not valid ISO format: {timestamp}")

        # Test detail timestamps if present
        if "details" in report:
            for i, detail in enumerate(report["details"]):
                compared_at = detail["compared_at"]
                try:
                    datetime.fromisoformat(compared_at)
                except ValueError:
                    pytest.fail(
                        f"details[{i}].compared_at is not valid ISO format: {compared_at}"
                    )


@pytest.mark.unit
class TestSeverityCaseInsensitivity:
    """Test case-insensitive handling of violation severity keys.

    The violation severity display logic must handle severity keys in any case
    (lowercase, uppercase, mixed case) and normalize them for consistent display.
    This prevents violations from being silently ignored when severity keys use
    unexpected casing.
    """

    def test_cli_handles_uppercase_severity_keys(
        self,
        service: ServiceDecisionReportGenerator,
    ) -> None:
        """Test CLI report correctly displays uppercase severity keys."""
        # Create summary with UPPERCASE severity keys (non-standard)
        summary = create_evidence_summary(
            invariant_violations=create_violation_breakdown(
                total_violations=5,
                by_type={"output_equivalence": 3, "latency": 2},
                by_severity={"CRITICAL": 2, "WARNING": 3},  # Uppercase keys
                new_violations=3,
                new_critical_violations=0,
            ),
        )

        report = service.generate_cli_report(summary, [], verbosity="standard")

        # Should display the severity counts correctly (normalized to lowercase)
        assert "2 critical" in report.lower()
        assert "3 warning" in report.lower()

    def test_cli_handles_mixed_case_severity_keys(
        self,
        service: ServiceDecisionReportGenerator,
    ) -> None:
        """Test CLI report correctly displays mixed case severity keys."""
        # Create summary with mixed case severity keys
        summary = create_evidence_summary(
            invariant_violations=create_violation_breakdown(
                total_violations=6,
                by_type={"schema": 6},
                by_severity={"Critical": 1, "Warning": 2, "Info": 3},  # Mixed case
                new_violations=4,
                new_critical_violations=0,
            ),
        )

        report = service.generate_cli_report(summary, [], verbosity="verbose")

        # Should display all severity counts correctly
        assert "1 critical" in report.lower()
        assert "2 warning" in report.lower()
        assert "3 info" in report.lower()

    def test_markdown_handles_uppercase_severity_keys(
        self,
        service: ServiceDecisionReportGenerator,
    ) -> None:
        """Test Markdown report correctly displays uppercase severity keys."""
        # Create summary with UPPERCASE severity keys
        summary = create_evidence_summary(
            invariant_violations=create_violation_breakdown(
                total_violations=4,
                by_type={"constraint": 4},
                by_severity={"CRITICAL": 1, "WARNING": 2, "INFO": 1},  # Uppercase
                new_violations=2,
                new_critical_violations=0,
            ),
        )

        report = service.generate_markdown_report(summary, [])

        # Should display severity labels capitalized consistently
        assert "| Critical | 1 |" in report
        assert "| Warning | 2 |" in report
        assert "| Info | 1 |" in report

    def test_markdown_severity_sort_order_with_mixed_case(
        self,
        service: ServiceDecisionReportGenerator,
    ) -> None:
        """Test Markdown sorts severities correctly regardless of case."""
        # Create summary with mixed case severity keys (wrong order)
        summary = create_evidence_summary(
            invariant_violations=create_violation_breakdown(
                total_violations=6,
                by_type={"test": 6},
                # Keys in wrong order and mixed case
                by_severity={"info": 1, "WARNING": 2, "CrItIcAl": 3},
                new_violations=4,
                new_critical_violations=0,
            ),
        )

        report = service.generate_markdown_report(summary, [])

        # Extract the severity table rows
        lines = report.split("\n")
        severity_rows = [
            line for line in lines if line.startswith("| ") and "|" in line[2:]
        ]

        # Find the severity values in order (after header)
        severity_values = []
        for row in severity_rows:
            cells = [cell.strip() for cell in row.split("|") if cell.strip()]
            if cells and cells[0] in ("Critical", "Warning", "Info"):
                severity_values.append(cells[0])

        # Critical should come before Warning, which should come before Info
        if severity_values:
            assert severity_values == ["Critical", "Warning", "Info"], (
                f"Severities not in correct order: {severity_values}"
            )

    def test_unknown_severity_keys_handled_gracefully(
        self,
        service: ServiceDecisionReportGenerator,
    ) -> None:
        """Test that unknown severity keys don't crash the report generation."""
        # Create summary with an unknown severity key
        summary = create_evidence_summary(
            invariant_violations=create_violation_breakdown(
                total_violations=3,
                by_type={"test": 3},
                by_severity={"critical": 1, "unknown_severity": 2},  # Unknown key
                new_violations=2,
                new_critical_violations=0,
            ),
        )

        # Should not raise - generates report with unknown severity at end
        cli_report = service.generate_cli_report(summary, [], verbosity="standard")
        md_report = service.generate_markdown_report(summary, [])

        # Critical should still be displayed
        assert "1 critical" in cli_report.lower()
        # Unknown severity should appear in markdown (sorted last)
        assert (
            "Unknown_severity" in md_report or "unknown_severity" in md_report.lower()
        )


# =============================================================================
# Export Function Tests
# =============================================================================


@pytest.mark.unit
class TestExportFunctions:
    """Test export functions for saving reports to files."""

    def test_save_to_file_markdown(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
        tmp_path: Path,
    ) -> None:
        """Test saving markdown report to file."""
        output_path = tmp_path / "report.md"
        service.save_to_file(
            sample_evidence_summary,
            sample_comparisons,
            output_path,
            output_format="markdown",
        )

        assert output_path.exists()
        content = output_path.read_text()
        assert "# Corpus Replay Evidence Report" in content
        assert sample_evidence_summary.corpus_id in content

    def test_save_to_file_cli(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
        tmp_path: Path,
    ) -> None:
        """Test saving CLI report to file."""
        output_path = tmp_path / "report.txt"
        service.save_to_file(
            sample_evidence_summary,
            sample_comparisons,
            output_path,
            output_format="cli",
        )

        assert output_path.exists()
        content = output_path.read_text()
        assert "CORPUS REPLAY EVIDENCE REPORT" in content
        assert sample_evidence_summary.corpus_id in content

    def test_save_to_file_json(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
        tmp_path: Path,
    ) -> None:
        """Test saving JSON report to file."""
        output_path = tmp_path / "report.json"
        service.save_to_file(
            sample_evidence_summary,
            sample_comparisons,
            output_path,
            output_format="json",
        )

        assert output_path.exists()
        content = output_path.read_text()

        # Verify it's valid JSON
        parsed = json.loads(content)
        assert "summary" in parsed
        assert "recommendation" in parsed
        assert parsed["summary"]["corpus_id"] == sample_evidence_summary.corpus_id

    def test_save_to_file_invalid_format_raises(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
        tmp_path: Path,
    ) -> None:
        """Test invalid format raises ModelOnexError."""
        output_path = tmp_path / "report.txt"

        with pytest.raises(ModelOnexError, match="Invalid format"):
            service.save_to_file(
                sample_evidence_summary,
                sample_comparisons,
                output_path,
                output_format="invalid",  # type: ignore[arg-type]
            )

    def test_save_to_markdown_convenience(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
        tmp_path: Path,
    ) -> None:
        """Test save_to_markdown convenience method."""
        output_path = tmp_path / "report.md"
        service.save_to_markdown(
            sample_evidence_summary, sample_comparisons, output_path
        )

        assert output_path.exists()
        content = output_path.read_text()
        assert "# Corpus Replay Evidence Report" in content

    def test_save_to_file_with_recommendation(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
        tmp_path: Path,
    ) -> None:
        """Test saving file with pre-generated recommendation."""
        recommendation = service.generate_recommendation(sample_evidence_summary)
        output_path = tmp_path / "report.md"

        service.save_to_file(
            sample_evidence_summary,
            sample_comparisons,
            output_path,
            output_format="markdown",
            recommendation=recommendation,
        )

        content = output_path.read_text()
        assert recommendation.action.upper() in content

    def test_save_to_file_creates_utf8_encoded(
        self,
        service: ServiceDecisionReportGenerator,
        sample_comparisons: list[ModelExecutionComparison],
        tmp_path: Path,
    ) -> None:
        """Test that saved files are properly UTF-8 encoded."""
        # Create summary with unicode characters
        summary = create_evidence_summary(
            invariant_violations=create_violation_breakdown(
                total_violations=2,
                by_type={"schema_\u2713": 1, "constraint_\u26a0": 1},
                by_severity={"warning": 2},
            ),
        )

        output_path = tmp_path / "report.md"
        service.save_to_file(
            summary, sample_comparisons, output_path, output_format="markdown"
        )

        # Read with explicit UTF-8 encoding
        content = output_path.read_text(encoding="utf-8")
        assert isinstance(content, str)
        # Unicode characters should be preserved
        assert "\u2713" in content or "\u26a0" in content

    def test_save_to_file_default_format_is_markdown(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
        tmp_path: Path,
    ) -> None:
        """Test that default format is markdown."""
        output_path = tmp_path / "report.md"
        # Call without explicit format
        service.save_to_file(sample_evidence_summary, sample_comparisons, output_path)

        content = output_path.read_text()
        # Should be markdown format (has markdown header)
        assert "# Corpus Replay Evidence Report" in content

    def test_save_to_file_empty_comparisons(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        tmp_path: Path,
    ) -> None:
        """Test saving with empty comparisons list."""
        output_path = tmp_path / "report.md"
        service.save_to_file(
            sample_evidence_summary, [], output_path, output_format="markdown"
        )

        assert output_path.exists()
        content = output_path.read_text()
        assert "# Corpus Replay Evidence Report" in content


# =============================================================================
# Generate All Formats Tests
# =============================================================================


@pytest.mark.unit
class TestGenerateAllFormats:
    """Test generate_all_formats convenience method."""

    def test_generate_all_formats_returns_all_formats(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test generate_all_formats returns cli, markdown, and json."""
        result = service.generate_all_formats(
            sample_evidence_summary, sample_comparisons
        )

        assert "cli" in result
        assert "markdown" in result
        assert "json" in result
        assert isinstance(result["cli"], str)
        assert isinstance(result["markdown"], str)
        assert isinstance(result["json"], str)

    def test_generate_all_formats_cli_has_correct_content(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test CLI format in generate_all_formats has expected content."""
        result = service.generate_all_formats(
            sample_evidence_summary, sample_comparisons
        )

        cli_output = result["cli"]
        assert "CORPUS REPLAY EVIDENCE REPORT" in cli_output
        assert sample_evidence_summary.corpus_id in cli_output

    def test_generate_all_formats_markdown_has_correct_content(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test Markdown format in generate_all_formats has expected content."""
        result = service.generate_all_formats(
            sample_evidence_summary, sample_comparisons
        )

        markdown_output = result["markdown"]
        assert "# Corpus Replay Evidence Report" in markdown_output
        assert sample_evidence_summary.corpus_id in markdown_output

    def test_generate_all_formats_json_is_valid(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test JSON format in generate_all_formats is valid JSON."""
        result = service.generate_all_formats(
            sample_evidence_summary, sample_comparisons
        )

        json_output = result["json"]
        # Should be valid JSON
        parsed = json.loads(json_output)
        assert "summary" in parsed
        assert "recommendation" in parsed
        assert parsed["summary"]["corpus_id"] == sample_evidence_summary.corpus_id

    def test_generate_all_formats_uses_same_recommendation(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test all formats use the same recommendation for consistency."""
        result = service.generate_all_formats(
            sample_evidence_summary, sample_comparisons
        )

        # Extract recommendation action from each format
        recommendation = service.generate_recommendation(sample_evidence_summary)

        # CLI should contain the action
        assert recommendation.action.upper() in result["cli"]

        # Markdown should contain the action
        assert recommendation.action.upper() in result["markdown"]

        # JSON should contain the action
        parsed_json = json.loads(result["json"])
        assert parsed_json["recommendation"]["action"] == recommendation.action

    def test_generate_all_formats_with_pre_generated_recommendation(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
        sample_comparisons: list[ModelExecutionComparison],
    ) -> None:
        """Test generate_all_formats with pre-generated recommendation."""
        # Generate recommendation once
        recommendation = service.generate_recommendation(sample_evidence_summary)

        result = service.generate_all_formats(
            sample_evidence_summary,
            sample_comparisons,
            recommendation=recommendation,
        )

        # All formats should use the provided recommendation
        assert recommendation.action.upper() in result["cli"]
        assert recommendation.action.upper() in result["markdown"]

        parsed_json = json.loads(result["json"])
        assert parsed_json["recommendation"]["action"] == recommendation.action
        assert parsed_json["recommendation"]["confidence"] == recommendation.confidence

    def test_generate_all_formats_empty_comparisons(
        self,
        service: ServiceDecisionReportGenerator,
        sample_evidence_summary: ModelEvidenceSummary,
    ) -> None:
        """Test generate_all_formats with empty comparisons list."""
        result = service.generate_all_formats(sample_evidence_summary, [])

        # Should still generate all three formats
        assert "cli" in result
        assert "markdown" in result
        assert "json" in result
        assert len(result["cli"]) > 0
        assert len(result["markdown"]) > 0
        assert len(result["json"]) > 0
