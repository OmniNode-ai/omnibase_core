# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for RendererReportMarkdown (OMN-1200).

This module tests the markdown rendering functionality including:
- Severity key normalization and aggregation
- Markdown special character escaping
- Table formatting

Thread Safety:
    All fixtures create immutable models (frozen=True), making them
    thread-safe for use with pytest-xdist parallel execution.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Literal

import pytest

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
from omnibase_core.rendering.renderer_report_markdown import (
    MARKDOWN_ESCAPE_CHARS,
    RendererReportMarkdown,
    _escape_markdown_table_cell,
)

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


# =============================================================================
# Escape Function Tests
# =============================================================================


@pytest.mark.unit
class TestEscapeMarkdownTableCell:
    """Tests for _escape_markdown_table_cell function."""

    def test_escapes_pipe_character(self) -> None:
        """Test that pipe characters are escaped to prevent table breaks."""
        result = _escape_markdown_table_cell("value|with|pipes")
        assert result == r"value\|with\|pipes"

    def test_escapes_asterisk(self) -> None:
        """Test that asterisks are escaped to prevent emphasis."""
        result = _escape_markdown_table_cell("value*with*asterisks")
        assert result == r"value\*with\*asterisks"

    def test_escapes_underscore(self) -> None:
        """Test that underscores are escaped to prevent emphasis."""
        result = _escape_markdown_table_cell("value_with_underscores")
        assert result == r"value\_with\_underscores"

    def test_escapes_backtick(self) -> None:
        """Test that backticks are escaped to prevent code formatting."""
        result = _escape_markdown_table_cell("value`with`backticks")
        assert result == r"value\`with\`backticks"

    def test_escapes_brackets(self) -> None:
        """Test that brackets are escaped to prevent links."""
        result = _escape_markdown_table_cell("value[with]brackets")
        assert result == r"value\[with\]brackets"

    def test_replaces_newlines_with_space(self) -> None:
        """Test that newlines are replaced with spaces to maintain table integrity."""
        result = _escape_markdown_table_cell("value\nwith\nnewlines")
        assert result == "value with newlines"

    def test_removes_carriage_returns(self) -> None:
        """Test that carriage returns are removed."""
        result = _escape_markdown_table_cell("value\rwith\rreturns")
        assert result == "valuewithreturns"

    def test_handles_empty_string(self) -> None:
        """Test that empty strings are handled correctly."""
        result = _escape_markdown_table_cell("")
        assert result == ""

    def test_handles_string_without_special_chars(self) -> None:
        """Test that strings without special chars pass through unchanged."""
        result = _escape_markdown_table_cell("normal text")
        assert result == "normal text"

    def test_handles_multiple_special_chars(self) -> None:
        """Test that multiple different special chars are all escaped."""
        result = _escape_markdown_table_cell("type|with*special_chars[and]more")
        assert result == r"type\|with\*special\_chars\[and\]more"

    def test_escape_chars_constant_completeness(self) -> None:
        """Test that all documented escape characters are in the constant."""
        expected_chars = {"|", "*", "_", "`", "[", "]", "\n", "\r"}
        assert set(MARKDOWN_ESCAPE_CHARS.keys()) == expected_chars


# =============================================================================
# Severity Aggregation Tests
# =============================================================================


@pytest.mark.unit
class TestSeverityAggregation:
    """Tests for severity key normalization and aggregation."""

    def test_aggregates_same_severity_different_cases(self) -> None:
        """Test that same severity with different cases is aggregated into single row.

        Given severity counts {"HIGH": 5, "High": 3, "high": 2}, the renderer should
        aggregate them into a single row with count 10, not three separate rows.
        """
        # Create summary with same severity in different cases
        violations = create_violation_breakdown(
            total_violations=10,
            by_type={"test": 10},
            by_severity={"HIGH": 5, "High": 3, "high": 2},  # Same severity, diff case
            new_violations=5,
            new_critical_violations=0,
            fixed_violations=0,
        )
        summary = create_evidence_summary(
            invariant_violations=violations,
            passed_count=90,
            failed_count=10,
            pass_rate=0.90,
            confidence_score=0.80,
        )
        recommendation = create_recommendation()

        report = RendererReportMarkdown.render(
            summary=summary,
            comparisons=[],
            recommendation=recommendation,
            generated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        # Should have only ONE row for "High" (aggregated) with count 10
        assert "| High | 10 |" in report

        # Should NOT have separate rows for different cases
        assert "| HIGH |" not in report
        assert "| high |" not in report

        # Count occurrences of "| High |" - should be exactly 1
        high_rows = [line for line in report.split("\n") if "| High |" in line]
        assert len(high_rows) == 1, (
            f"Expected 1 High row, got {len(high_rows)}: {high_rows}"
        )

    def test_aggregates_multiple_severities_with_mixed_cases(self) -> None:
        """Test aggregation of multiple different severities each with mixed cases."""
        violations = create_violation_breakdown(
            total_violations=20,
            by_type={"test": 20},
            by_severity={
                "CRITICAL": 3,
                "Critical": 2,  # Should aggregate with CRITICAL
                "WARNING": 5,
                "warning": 3,  # Should aggregate with WARNING
                "Info": 7,  # Single occurrence, different case
            },
            new_violations=10,
            new_critical_violations=3,
            fixed_violations=2,
        )
        summary = create_evidence_summary(
            invariant_violations=violations,
            passed_count=80,
            failed_count=20,
            pass_rate=0.80,
            confidence_score=0.75,
        )
        recommendation = create_recommendation()

        report = RendererReportMarkdown.render(
            summary=summary,
            comparisons=[],
            recommendation=recommendation,
            generated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        # Should have aggregated counts
        assert "| Critical | 5 |" in report  # 3 + 2
        assert "| Warning | 8 |" in report  # 5 + 3
        assert "| Info | 7 |" in report  # Single occurrence

        # Should NOT have uppercase or mixed case rows
        assert "| CRITICAL |" not in report
        assert "| WARNING |" not in report

    def test_severity_sort_order_after_aggregation(self) -> None:
        """Test that severities are sorted correctly after aggregation."""
        violations = create_violation_breakdown(
            total_violations=15,
            by_type={"test": 15},
            by_severity={
                # Intentionally out of order and mixed case
                "info": 5,
                "WARNING": 4,
                "Critical": 6,
            },
            new_violations=8,
            new_critical_violations=3,
            fixed_violations=0,
        )
        summary = create_evidence_summary(
            invariant_violations=violations,
            passed_count=85,
            failed_count=15,
            pass_rate=0.85,
            confidence_score=0.80,
        )
        recommendation = create_recommendation()

        report = RendererReportMarkdown.render(
            summary=summary,
            comparisons=[],
            recommendation=recommendation,
            generated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        # Extract severity rows from the report
        lines = report.split("\n")
        severity_rows: list[str] = []
        in_severity_section = False
        for line in lines:
            if "### By Severity" in line:
                in_severity_section = True
                continue
            if in_severity_section:
                if line.startswith("| ") and "|" in line[2:]:
                    cells = [cell.strip() for cell in line.split("|") if cell.strip()]
                    if cells and cells[0] in ("Critical", "Warning", "Info"):
                        severity_rows.append(cells[0])
                elif line.startswith("#") or (line.strip() == "" and severity_rows):
                    break

        # Critical should come first, then Warning, then Info
        assert severity_rows == ["Critical", "Warning", "Info"], (
            f"Severities not in correct order: {severity_rows}"
        )


# =============================================================================
# Content Escaping Integration Tests
# =============================================================================


@pytest.mark.unit
class TestContentEscaping:
    """Tests for markdown escaping in rendered content."""

    def test_escapes_violation_type_with_special_chars(self) -> None:
        """Test that violation types with special characters are escaped."""
        violations = create_violation_breakdown(
            total_violations=3,
            by_type={
                "type|with|pipes": 1,
                "type_with_underscores": 1,
                "type*with*asterisks": 1,
            },
            by_severity={"warning": 3},
            new_violations=2,
            new_critical_violations=0,
            fixed_violations=0,
        )
        summary = create_evidence_summary(
            invariant_violations=violations,
            passed_count=97,
            failed_count=3,
            pass_rate=0.97,
            confidence_score=0.90,
        )
        recommendation = create_recommendation()

        report = RendererReportMarkdown.render(
            summary=summary,
            comparisons=[],
            recommendation=recommendation,
            generated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        # Pipes should be escaped to prevent table breaks
        assert r"type\|with\|pipes" in report

        # Underscores should be escaped to prevent emphasis
        assert r"type\_with\_underscores" in report

        # Asterisks should be escaped to prevent emphasis
        assert r"type\*with\*asterisks" in report

    def test_table_integrity_with_escaped_content(self) -> None:
        """Test that tables remain valid after escaping special characters."""
        violations = create_violation_breakdown(
            total_violations=1,
            by_type={"dangerous|type|name": 1},
            by_severity={"warning": 1},
            new_violations=1,
            new_critical_violations=0,
            fixed_violations=0,
        )
        summary = create_evidence_summary(
            invariant_violations=violations,
            passed_count=99,
            failed_count=1,
            pass_rate=0.99,
            confidence_score=0.95,
        )
        recommendation = create_recommendation()

        report = RendererReportMarkdown.render(
            summary=summary,
            comparisons=[],
            recommendation=recommendation,
            generated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        # Find the By Type table and verify it has correct structure
        lines = report.split("\n")
        in_type_section = False
        type_table_rows: list[str] = []
        for line in lines:
            if "### By Type" in line:
                in_type_section = True
                continue
            if in_type_section:
                if line.startswith("|"):
                    type_table_rows.append(line)
                elif line.startswith("#") or (
                    line.strip() == "" and len(type_table_rows) > 2
                ):
                    break

        # Should have header, separator, and data row
        assert len(type_table_rows) >= 3, (
            f"Expected at least 3 table rows, got: {type_table_rows}"
        )

        # Each row should have exactly 3 pipe characters (| Type | Count |)
        for row in type_table_rows:
            # Count unescaped pipes (not preceded by backslash)
            unescaped_pipes = len(re.findall(r"(?<!\\)\|", row))
            assert unescaped_pipes == 3, (
                f"Row should have 3 unescaped pipes, got {unescaped_pipes}: {row}"
            )
