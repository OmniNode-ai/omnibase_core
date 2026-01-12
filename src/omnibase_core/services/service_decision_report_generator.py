# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Decision report generator service for corpus replay evidence (OMN-1199).

Generates decision-ready reports from corpus replay evidence in multiple formats:
- CLI: Formatted terminal output with configurable verbosity
- JSON: Structured data for machine consumption
- Markdown: GitHub-flavored markdown for PRs and documentation

Thread Safety:
    ServiceDecisionReportGenerator is stateless and thread-safe. All methods
    are pure functions that take inputs and return outputs without modifying
    any shared state.
"""

from datetime import UTC, datetime
from typing import Literal

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.comparison.model_execution_comparison import (
    ModelExecutionComparison,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.evidence.model_decision_recommendation import (
    ModelDecisionRecommendation,
)
from omnibase_core.models.evidence.model_evidence_summary import ModelEvidenceSummary
from omnibase_core.types.typed_dict_decision_report import TypedDictDecisionReport

# Report formatting constants
REPORT_WIDTH = 80
REPORT_VERSION = "1.0.0"
SEPARATOR_CHAR = "="
SEPARATOR_LINE = SEPARATOR_CHAR * REPORT_WIDTH
SUBSECTION_CHAR = "-"

# Comparison display limits
COMPARISON_LIMIT_CLI_VERBOSE = 10
COMPARISON_LIMIT_MARKDOWN = 50

# Cost data unavailability messages (consistent terminology across formats)
COST_NA_CLI = "Cost:     N/A (incomplete cost data)"
COST_NA_MARKDOWN = "_Cost data not available (incomplete data)_"
COST_NA_WARNING = "Cost data incomplete - manual cost review recommended"


class ServiceDecisionReportGenerator:
    """Generate decision-ready reports from corpus replay evidence.

    This service transforms ModelEvidenceSummary and ModelExecutionComparison data
    into human-readable and machine-readable report formats suitable for different
    stakeholders and use cases.

    Runtime Configuration:
        All recommendation thresholds can be customized at instantiation time.
        If not provided, class-level constants are used as defaults.

    Thread Safety:
        This service is stateless per-call and thread-safe. Instance attributes
        are set once during initialization and never modified. All methods are
        pure functions that take inputs and return outputs without modifying
        any shared state. Multiple threads can safely call any method concurrently.

    Example:
        >>> from omnibase_core.services.service_decision_report_generator import (
        ...     ServiceDecisionReportGenerator
        ... )
        >>> # Use default thresholds
        >>> generator = ServiceDecisionReportGenerator()
        >>> cli_report = generator.generate_cli_report(summary, comparisons)
        >>> print(cli_report)
        >>>
        >>> # Custom thresholds for stricter review
        >>> strict_generator = ServiceDecisionReportGenerator(
        ...     confidence_approve_threshold=0.95,
        ...     pass_rate_minimum=0.85,
        ... )

    .. versionadded:: 0.6.5
    """

    # Recommendation thresholds - confidence levels
    CONFIDENCE_APPROVE_THRESHOLD: float = 0.9
    CONFIDENCE_REVIEW_THRESHOLD: float = 0.7

    # Recommendation thresholds - pass rate
    PASS_RATE_OPTIMAL: float = 0.95
    PASS_RATE_MINIMUM: float = 0.70

    # Recommendation thresholds - latency regression (percent)
    LATENCY_BLOCKER_PERCENT: float = 50.0
    LATENCY_WARNING_PERCENT: float = 20.0

    # Recommendation thresholds - cost regression (percent)
    COST_BLOCKER_PERCENT: float = 50.0
    COST_WARNING_PERCENT: float = 20.0

    def __init__(
        self,
        confidence_approve_threshold: float | None = None,
        confidence_review_threshold: float | None = None,
        pass_rate_optimal: float | None = None,
        pass_rate_minimum: float | None = None,
        latency_blocker_percent: float | None = None,
        latency_warning_percent: float | None = None,
        cost_blocker_percent: float | None = None,
        cost_warning_percent: float | None = None,
    ) -> None:
        """Initialize report generator with optional threshold overrides.

        Args:
            confidence_approve_threshold: Minimum confidence for auto-approve.
                Defaults to CONFIDENCE_APPROVE_THRESHOLD (0.9).
            confidence_review_threshold: Minimum confidence for review recommendation.
                Defaults to CONFIDENCE_REVIEW_THRESHOLD (0.7).
            pass_rate_optimal: Target pass rate (below triggers warning).
                Defaults to PASS_RATE_OPTIMAL (0.95).
            pass_rate_minimum: Minimum pass rate (below triggers blocker).
                Defaults to PASS_RATE_MINIMUM (0.70).
            latency_blocker_percent: Latency increase percentage that triggers blocker.
                Defaults to LATENCY_BLOCKER_PERCENT (50.0).
            latency_warning_percent: Latency increase percentage that triggers warning.
                Defaults to LATENCY_WARNING_PERCENT (20.0).
            cost_blocker_percent: Cost increase percentage that triggers blocker.
                Defaults to COST_BLOCKER_PERCENT (50.0).
            cost_warning_percent: Cost increase percentage that triggers warning.
                Defaults to COST_WARNING_PERCENT (20.0).
        """
        self.confidence_approve_threshold = (
            confidence_approve_threshold
            if confidence_approve_threshold is not None
            else self.CONFIDENCE_APPROVE_THRESHOLD
        )
        self.confidence_review_threshold = (
            confidence_review_threshold
            if confidence_review_threshold is not None
            else self.CONFIDENCE_REVIEW_THRESHOLD
        )
        self.pass_rate_optimal = (
            pass_rate_optimal
            if pass_rate_optimal is not None
            else self.PASS_RATE_OPTIMAL
        )
        self.pass_rate_minimum = (
            pass_rate_minimum
            if pass_rate_minimum is not None
            else self.PASS_RATE_MINIMUM
        )
        self.latency_blocker_percent = (
            latency_blocker_percent
            if latency_blocker_percent is not None
            else self.LATENCY_BLOCKER_PERCENT
        )
        self.latency_warning_percent = (
            latency_warning_percent
            if latency_warning_percent is not None
            else self.LATENCY_WARNING_PERCENT
        )
        self.cost_blocker_percent = (
            cost_blocker_percent
            if cost_blocker_percent is not None
            else self.COST_BLOCKER_PERCENT
        )
        self.cost_warning_percent = (
            cost_warning_percent
            if cost_warning_percent is not None
            else self.COST_WARNING_PERCENT
        )

        # Validate threshold ranges
        if not (0.0 <= self.confidence_approve_threshold <= 1.0):
            raise ModelOnexError(
                message=f"confidence_approve_threshold must be between 0.0 and 1.0, "
                f"got {self.confidence_approve_threshold}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if not (0.0 <= self.confidence_review_threshold <= 1.0):
            raise ModelOnexError(
                message=f"confidence_review_threshold must be between 0.0 and 1.0, "
                f"got {self.confidence_review_threshold}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if not (0.0 <= self.pass_rate_optimal <= 1.0):
            raise ModelOnexError(
                message=f"pass_rate_optimal must be between 0.0 and 1.0, "
                f"got {self.pass_rate_optimal}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if not (0.0 <= self.pass_rate_minimum <= 1.0):
            raise ModelOnexError(
                message=f"pass_rate_minimum must be between 0.0 and 1.0, "
                f"got {self.pass_rate_minimum}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if self.latency_blocker_percent < 0:
            raise ModelOnexError(
                message=f"latency_blocker_percent must be >= 0, "
                f"got {self.latency_blocker_percent}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if self.latency_warning_percent < 0:
            raise ModelOnexError(
                message=f"latency_warning_percent must be >= 0, "
                f"got {self.latency_warning_percent}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if self.cost_blocker_percent < 0:
            raise ModelOnexError(
                message=f"cost_blocker_percent must be >= 0, "
                f"got {self.cost_blocker_percent}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if self.cost_warning_percent < 0:
            raise ModelOnexError(
                message=f"cost_warning_percent must be >= 0, "
                f"got {self.cost_warning_percent}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

    def generate_cli_report(
        self,
        summary: ModelEvidenceSummary,
        comparisons: list[ModelExecutionComparison],
        verbosity: Literal["minimal", "standard", "verbose"] = "standard",
        recommendation: ModelDecisionRecommendation | None = None,
    ) -> str:
        """Generate formatted CLI output for terminal display.

        Creates a fixed-width (80 character) formatted report suitable for
        terminal output with configurable verbosity levels.

        Args:
            summary: Aggregated evidence summary from corpus replay.
            comparisons: Individual execution comparisons (used in verbose mode).
            verbosity: Output detail level:
                - "minimal": Headline and recommendation only
                - "standard": Full summary with sections
                - "verbose": Everything including comparison details
            recommendation: Pre-generated recommendation. If None, generates a new one.
                Providing this avoids redundant computation when generating multiple formats.

        Returns:
            Formatted string report for terminal display.

        Example:
            >>> report = generator.generate_cli_report(summary, [], "standard")
            >>> print(report)
        """
        lines: list[str] = []

        if verbosity == "minimal":
            return self._generate_minimal_cli_report(summary, recommendation)

        # Header
        lines.append(SEPARATOR_LINE)
        lines.append(self._center_text("CORPUS REPLAY EVIDENCE REPORT"))
        lines.append(SEPARATOR_LINE)
        lines.append("")

        # Summary section
        lines.append("SUMMARY")
        lines.append(SUBSECTION_CHAR * len("SUMMARY"))
        lines.append(f"Corpus: {summary.corpus_id}")
        lines.append(
            f"Baseline: {summary.baseline_version} | Replay: {summary.replay_version}"
        )
        pass_rate_pct = summary.pass_rate * 100
        lines.append(
            f"Executions: {summary.passed_count}/{summary.total_executions} "
            f"passed ({pass_rate_pct:.0f}%)"
        )
        lines.append("")

        # Invariant violations section
        violation_count = summary.invariant_violations.total_violations
        lines.append(f"INVARIANT VIOLATIONS ({violation_count})")
        lines.append(
            SUBSECTION_CHAR * (len(f"INVARIANT VIOLATIONS ({violation_count})"))
        )

        if violation_count == 0:
            lines.append("No violations detected.")
        else:
            by_severity = summary.invariant_violations.by_severity
            by_type = summary.invariant_violations.by_type

            # Severity and type are independent aggregations in ModelInvariantViolationBreakdown.
            # by_severity counts violations by severity level (critical/warning/info).
            # by_type counts violations by type (e.g., "schema_mismatch", "constraint_violation").
            # These cannot be correlated since we don't have per-violation severity-type pairs.
            severity_parts = []
            critical_count = by_severity.get("critical", 0)
            warning_count = by_severity.get("warning", 0)
            info_count = by_severity.get("info", 0)

            if critical_count > 0:
                severity_parts.append(f"{critical_count} critical")
            if warning_count > 0:
                severity_parts.append(f"{warning_count} warning")
            if verbosity == "verbose" and info_count > 0:
                severity_parts.append(f"{info_count} info")

            if severity_parts:
                lines.append(f"Severity: {', '.join(severity_parts)}")

            # Show type breakdown without severity labels
            # (types and severities are independent aggregations)
            if by_type:
                lines.append("By type:")
                for violation_type, count in sorted(by_type.items()):
                    lines.append(f"  - {violation_type}: {count} violation(s)")

        lines.append("")

        # Performance section
        lines.append("PERFORMANCE")
        lines.append(SUBSECTION_CHAR * len("PERFORMANCE"))

        latency_delta = summary.latency_stats.delta_avg_percent
        latency_sign = "+" if latency_delta > 0 else ""
        baseline_latency = summary.latency_stats.baseline_avg_ms
        replay_latency = summary.latency_stats.replay_avg_ms
        lines.append(
            f"Latency:  {latency_sign}{latency_delta:.0f}% "
            f"(avg {baseline_latency:.0f}ms -> {replay_latency:.0f}ms)"
        )

        if summary.cost_stats is not None:
            cost_delta = summary.cost_stats.delta_percent
            cost_sign = "+" if cost_delta > 0 else ""
            baseline_cost = summary.cost_stats.baseline_avg_per_execution
            replay_cost = summary.cost_stats.replay_avg_per_execution
            lines.append(
                f"Cost:     {cost_sign}{cost_delta:.0f}% "
                f"(${baseline_cost:.4f} -> ${replay_cost:.4f} per execution)"
            )
        else:
            lines.append(COST_NA_CLI)

        lines.append("")

        # Recommendation section
        if recommendation is None:
            recommendation = self.generate_recommendation(summary)
        action_upper = recommendation.action.upper()
        lines.append(f"RECOMMENDATION: {action_upper}")
        lines.append(SUBSECTION_CHAR * (len(f"RECOMMENDATION: {action_upper}")))
        lines.append(f"Confidence: {recommendation.confidence:.0%}")
        lines.append("")

        if recommendation.blockers:
            lines.append("Blockers:")
            for blocker in recommendation.blockers:
                lines.append(f"  - {blocker}")
            lines.append("")

        if recommendation.warnings:
            lines.append("Warnings:")
            for warning in recommendation.warnings:
                lines.append(f"  - {warning}")
            lines.append("")

        if recommendation.next_steps:
            lines.append("Next Steps:")
            for i, step in enumerate(recommendation.next_steps, 1):
                lines.append(f"  {i}. {step}")
            lines.append("")

        # Verbose: include comparison details
        if verbosity == "verbose" and comparisons:
            lines.append("COMPARISON DETAILS")
            lines.append(SUBSECTION_CHAR * len("COMPARISON DETAILS"))
            for comparison in comparisons[:COMPARISON_LIMIT_CLI_VERBOSE]:
                status = "PASS" if comparison.output_match else "FAIL"
                lines.append(
                    f"[{status}] {comparison.comparison_id} | "
                    f"Latency: {comparison.latency_delta_percent:+.1f}%"
                )
            if len(comparisons) > COMPARISON_LIMIT_CLI_VERBOSE:
                lines.append(
                    f"... and {len(comparisons) - COMPARISON_LIMIT_CLI_VERBOSE} more comparisons"
                )
            lines.append("")

        lines.append(SEPARATOR_LINE)

        return "\n".join(lines)

    def _generate_minimal_cli_report(
        self,
        summary: ModelEvidenceSummary,
        recommendation: ModelDecisionRecommendation | None = None,
    ) -> str:
        """Generate minimal CLI report (headline + recommendation only).

        Args:
            summary: Aggregated evidence summary.
            recommendation: Pre-generated recommendation. If None, generates a new one.

        Returns:
            Minimal formatted report string.
        """
        if recommendation is None:
            recommendation = self.generate_recommendation(summary)
        lines = [
            summary.headline,
            f"Recommendation: {recommendation.action.upper()} "
            f"(confidence: {recommendation.confidence:.0%})",
        ]
        return "\n".join(lines)

    def _center_text(self, text: str) -> str:
        """Center text within REPORT_WIDTH, truncating if necessary.

        Args:
            text: Text to center.

        Returns:
            Centered text string, truncated with ellipsis if too long.
        """
        if len(text) > REPORT_WIDTH:
            return text[: REPORT_WIDTH - 3] + "..."
        return text.center(REPORT_WIDTH)

    def generate_json_report(
        self,
        summary: ModelEvidenceSummary,
        comparisons: list[ModelExecutionComparison],
        include_details: bool = False,
        recommendation: ModelDecisionRecommendation | None = None,
        generated_at: datetime | None = None,
    ) -> TypedDictDecisionReport:
        """Generate structured JSON report for machine consumption.

        Creates a JSON-serializable dictionary with all evidence data suitable
        for API responses, storage, or further processing. Output is deterministic
        when a fixed `generated_at` timestamp is provided.

        Args:
            summary: Aggregated evidence summary from corpus replay.
            comparisons: Individual execution comparisons.
            include_details: Whether to include individual comparison details.
            recommendation: Pre-generated recommendation. If None, generates a new one.
                Providing this avoids redundant computation when generating multiple formats.
            generated_at: Optional timestamp for report generation. If None, uses
                current UTC time. Providing a fixed timestamp enables deterministic
                output for testing.

        Returns:
            TypedDictDecisionReport with report data.

        Example:
            >>> report = generator.generate_json_report(summary, comparisons)
            >>> json_str = json.dumps(report, sort_keys=True)
        """
        if recommendation is None:
            recommendation = self.generate_recommendation(summary)

        report: TypedDictDecisionReport = {
            "report_version": REPORT_VERSION,
            "generated_at": generated_at.isoformat()
            if generated_at
            else datetime.now(UTC).isoformat(),
            "summary": {
                "summary_id": summary.summary_id,
                "corpus_id": summary.corpus_id,
                "baseline_version": summary.baseline_version,
                "replay_version": summary.replay_version,
                "total_executions": summary.total_executions,
                "passed_count": summary.passed_count,
                "failed_count": summary.failed_count,
                "pass_rate": summary.pass_rate,
                "confidence_score": summary.confidence_score,
                "headline": summary.headline,
                "started_at": summary.started_at.isoformat(),
                "ended_at": summary.ended_at.isoformat(),
            },
            "violations": {
                "total": summary.invariant_violations.total_violations,
                "by_type": summary.invariant_violations.by_type,
                "by_severity": summary.invariant_violations.by_severity,
                "new_violations": summary.invariant_violations.new_violations,
                "new_critical_violations": (
                    summary.invariant_violations.new_critical_violations
                ),
                "fixed_violations": summary.invariant_violations.fixed_violations,
            },
            "performance": {
                "latency": {
                    "baseline_avg_ms": summary.latency_stats.baseline_avg_ms,
                    "replay_avg_ms": summary.latency_stats.replay_avg_ms,
                    "delta_avg_ms": summary.latency_stats.delta_avg_ms,
                    "delta_avg_percent": summary.latency_stats.delta_avg_percent,
                    "baseline_p50_ms": summary.latency_stats.baseline_p50_ms,
                    "replay_p50_ms": summary.latency_stats.replay_p50_ms,
                    "delta_p50_percent": summary.latency_stats.delta_p50_percent,
                    "baseline_p95_ms": summary.latency_stats.baseline_p95_ms,
                    "replay_p95_ms": summary.latency_stats.replay_p95_ms,
                    "delta_p95_percent": summary.latency_stats.delta_p95_percent,
                },
                "cost": None,
            },
            "recommendation": {
                "action": recommendation.action,
                "confidence": recommendation.confidence,
                "blockers": recommendation.blockers,
                "warnings": recommendation.warnings,
                "next_steps": recommendation.next_steps,
                "rationale": recommendation.rationale,
            },
        }

        # Add cost data if available
        if summary.cost_stats is not None:
            report["performance"]["cost"] = {
                "baseline_total": summary.cost_stats.baseline_total,
                "replay_total": summary.cost_stats.replay_total,
                "delta_total": summary.cost_stats.delta_total,
                "delta_percent": summary.cost_stats.delta_percent,
                "baseline_avg_per_execution": (
                    summary.cost_stats.baseline_avg_per_execution
                ),
                "replay_avg_per_execution": summary.cost_stats.replay_avg_per_execution,
            }

        # Add details if requested
        if include_details and comparisons:
            report["details"] = [
                {
                    "comparison_id": str(c.comparison_id),
                    "baseline_execution_id": str(c.baseline_execution_id),
                    "replay_execution_id": str(c.replay_execution_id),
                    "input_hash": c.input_hash,
                    "input_hash_match": c.input_hash_match,
                    "output_match": c.output_match,
                    "baseline_latency_ms": c.baseline_latency_ms,
                    "replay_latency_ms": c.replay_latency_ms,
                    "latency_delta_ms": c.latency_delta_ms,
                    "latency_delta_percent": c.latency_delta_percent,
                    "baseline_cost": c.baseline_cost,
                    "replay_cost": c.replay_cost,
                    "cost_delta": c.cost_delta,
                    "cost_delta_percent": c.cost_delta_percent,
                    "compared_at": c.compared_at.isoformat(),
                }
                for c in comparisons
            ]

        return report

    def generate_markdown_report(
        self,
        summary: ModelEvidenceSummary,
        comparisons: list[ModelExecutionComparison],
        include_details: bool = True,
        recommendation: ModelDecisionRecommendation | None = None,
        generated_at: datetime | None = None,
    ) -> str:
        """Generate Markdown report for PR/documentation.

        Creates GitHub-flavored markdown suitable for pull request descriptions,
        documentation, or other markdown-rendering contexts.

        Args:
            summary: Aggregated evidence summary from corpus replay.
            comparisons: Individual execution comparisons.
            include_details: Whether to include individual comparison details.
            recommendation: Pre-generated recommendation. If None, generates a new one.
                Providing this avoids redundant computation when generating multiple formats.
            generated_at: Optional timestamp for report generation. If None, uses
                current UTC time. Providing a fixed timestamp enables deterministic
                output for testing.

        Returns:
            GitHub-flavored markdown string.

        Example:
            >>> md_report = generator.generate_markdown_report(summary, comparisons)
            >>> with open("report.md", "w") as f:
            ...     f.write(md_report)
        """
        if recommendation is None:
            recommendation = self.generate_recommendation(summary)
        lines: list[str] = []

        # Header
        lines.append("# Corpus Replay Evidence Report")
        lines.append("")
        generated_at_str = (
            generated_at.isoformat() if generated_at else datetime.now(UTC).isoformat()
        )
        lines.append(f"> **Generated**: {generated_at_str}")
        lines.append("")

        # Summary section
        lines.append("## Summary")
        lines.append("")
        lines.append(f"**Corpus**: `{summary.corpus_id}`")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Baseline Version | `{summary.baseline_version}` |")
        lines.append(f"| Replay Version | `{summary.replay_version}` |")
        lines.append(
            f"| Pass Rate | {summary.passed_count}/{summary.total_executions} "
            f"({summary.pass_rate:.1%}) |"
        )
        lines.append(f"| Confidence | {summary.confidence_score:.1%} |")
        lines.append("")
        lines.append(f"**Headline**: {summary.headline}")
        lines.append("")

        # Recommendation section
        lines.append("## Recommendation")
        lines.append("")

        # Use emoji indicators based on action
        emoji = {
            "approve": ":white_check_mark:",
            "review": ":warning:",
            "reject": ":x:",
        }
        lines.append(
            f"{emoji.get(recommendation.action, '')} "
            f"**{recommendation.action.upper()}** "
            f"(confidence: {recommendation.confidence:.0%})"
        )
        lines.append("")

        if recommendation.rationale:
            lines.append(f"_{recommendation.rationale}_")
            lines.append("")

        if recommendation.blockers:
            lines.append("### Blockers")
            lines.append("")
            for blocker in recommendation.blockers:
                lines.append(f"- :x: {blocker}")
            lines.append("")

        if recommendation.warnings:
            lines.append("### Warnings")
            lines.append("")
            for warning in recommendation.warnings:
                lines.append(f"- :warning: {warning}")
            lines.append("")

        if recommendation.next_steps:
            lines.append("### Next Steps")
            lines.append("")
            for i, step in enumerate(recommendation.next_steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        # Invariant Violations section
        lines.append("## Invariant Violations")
        lines.append("")

        violation_count = summary.invariant_violations.total_violations
        if violation_count == 0:
            lines.append(":white_check_mark: No violations detected.")
        else:
            lines.append(
                f":warning: **{violation_count}** violation(s) detected "
                f"({summary.invariant_violations.new_violations} new, "
                f"{summary.invariant_violations.fixed_violations} fixed)"
            )
            lines.append("")

            # Violations by type table
            if summary.invariant_violations.by_type:
                lines.append("### By Type")
                lines.append("")
                lines.append("| Type | Count |")
                lines.append("|------|-------|")
                for vtype, count in sorted(
                    summary.invariant_violations.by_type.items()
                ):
                    lines.append(f"| {vtype} | {count} |")
                lines.append("")

            # Violations by severity table
            if summary.invariant_violations.by_severity:
                lines.append("### By Severity")
                lines.append("")
                lines.append("| Severity | Count |")
                lines.append("|----------|-------|")
                for severity, count in sorted(
                    summary.invariant_violations.by_severity.items(),
                    key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(
                        x[0], 99
                    ),
                ):
                    lines.append(f"| {severity} | {count} |")
                lines.append("")

        # Performance section
        lines.append("## Performance")
        lines.append("")

        # Latency table
        lines.append("### Latency")
        lines.append("")
        latency = summary.latency_stats
        latency_emoji = (
            ":white_check_mark:" if latency.delta_avg_percent <= 0 else ":warning:"
        )
        lines.append(
            f"{latency_emoji} Average latency change: "
            f"**{latency.delta_avg_percent:+.1f}%**"
        )
        lines.append("")
        lines.append("| Metric | Baseline | Replay | Delta |")
        lines.append("|--------|----------|--------|-------|")
        lines.append(
            f"| Average | {latency.baseline_avg_ms:.1f}ms | "
            f"{latency.replay_avg_ms:.1f}ms | "
            f"{latency.delta_avg_ms:+.1f}ms ({latency.delta_avg_percent:+.1f}%) |"
        )
        lines.append(
            f"| P50 | {latency.baseline_p50_ms:.1f}ms | "
            f"{latency.replay_p50_ms:.1f}ms | "
            f"{latency.delta_p50_percent:+.1f}% |"
        )
        lines.append(
            f"| P95 | {latency.baseline_p95_ms:.1f}ms | "
            f"{latency.replay_p95_ms:.1f}ms | "
            f"{latency.delta_p95_percent:+.1f}% |"
        )
        lines.append("")

        # Cost table (if available)
        lines.append("### Cost")
        lines.append("")
        if summary.cost_stats is not None:
            cost = summary.cost_stats
            cost_emoji = (
                ":white_check_mark:" if cost.delta_percent <= 0 else ":warning:"
            )
            lines.append(
                f"{cost_emoji} Total cost change: **{cost.delta_percent:+.1f}%**"
            )
            lines.append("")
            lines.append("| Metric | Baseline | Replay | Delta |")
            lines.append("|--------|----------|--------|-------|")
            lines.append(
                f"| Total | ${cost.baseline_total:.4f} | "
                f"${cost.replay_total:.4f} | "
                f"${cost.delta_total:+.4f} ({cost.delta_percent:+.1f}%) |"
            )
            lines.append(
                f"| Avg/Execution | ${cost.baseline_avg_per_execution:.6f} | "
                f"${cost.replay_avg_per_execution:.6f} | - |"
            )
        else:
            lines.append(COST_NA_MARKDOWN)
        lines.append("")

        # Details section (if requested)
        if include_details and comparisons:
            lines.append("## Comparison Details")
            lines.append("")
            lines.append("<details>")
            lines.append("<summary>Click to expand comparison details</summary>")
            lines.append("")
            lines.append("| Status | Comparison ID | Latency Delta | Output Match |")
            lines.append("|--------|---------------|---------------|--------------|")

            for c in comparisons[:COMPARISON_LIMIT_MARKDOWN]:
                status = ":white_check_mark:" if c.output_match else ":x:"
                lines.append(
                    f"| {status} | `{str(c.comparison_id)[:8]}...` | "
                    f"{c.latency_delta_percent:+.1f}% | "
                    f"{'Yes' if c.output_match else 'No'} |"
                )

            if len(comparisons) > COMPARISON_LIMIT_MARKDOWN:
                lines.append("")
                lines.append(
                    f"_... and {len(comparisons) - COMPARISON_LIMIT_MARKDOWN} more comparisons_"
                )

            lines.append("")
            lines.append("</details>")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"_Report version: {REPORT_VERSION}_")

        return "\n".join(lines)

    def generate_recommendation(
        self,
        summary: ModelEvidenceSummary,
    ) -> ModelDecisionRecommendation:
        """Generate actionable recommendation from evidence.

        Analyzes the evidence summary and generates a recommendation with
        blockers, warnings, and next steps based on configurable instance
        thresholds. Thresholds can be customized at instantiation or use
        class constant defaults:

        - confidence_approve_threshold: Minimum confidence for auto-approve
        - confidence_review_threshold: Minimum confidence for review recommendation
        - pass_rate_optimal: Target pass rate (below triggers warning)
        - pass_rate_minimum: Minimum pass rate (below triggers blocker)
        - latency_blocker_percent: Latency increase that triggers blocker
        - latency_warning_percent: Latency increase that triggers warning
        - cost_blocker_percent: Cost increase that triggers blocker
        - cost_warning_percent: Cost increase that triggers warning

        Recommendation Logic:
            - **approve**: confidence >= confidence_approve_threshold AND
              no critical violations AND no blockers
            - **review**: confidence >= confidence_review_threshold AND
              no critical violations (warnings OK)
            - **reject**: confidence < confidence_review_threshold OR
              critical violations present

        Args:
            summary: Aggregated evidence summary from corpus replay.

        Returns:
            ModelDecisionRecommendation with action, confidence, blockers,
            warnings, and next steps.

        Example:
            >>> recommendation = generator.generate_recommendation(summary)
            >>> if recommendation.action == "approve":
            ...     print("Safe to merge!")
        """
        blockers: list[str] = []
        warnings: list[str] = []
        next_steps: list[str] = []

        confidence = summary.confidence_score
        violations = summary.invariant_violations

        # Check for critical violations (blockers)
        if violations.new_critical_violations > 0:
            blockers.append(
                f"{violations.new_critical_violations} new critical "
                f"invariant violation(s) detected"
            )

        # Check pass rate
        if summary.pass_rate < self.pass_rate_optimal:
            if summary.pass_rate < self.pass_rate_minimum:
                blockers.append(
                    f"Pass rate too low: {summary.pass_rate:.0%} "
                    f"(minimum: {self.pass_rate_minimum:.0%})"
                )
            else:
                warnings.append(
                    f"Pass rate below optimal: {summary.pass_rate:.0%} "
                    f"(target: {self.pass_rate_optimal:.0%})"
                )

        # Check latency regression
        latency_delta = summary.latency_stats.delta_avg_percent
        if latency_delta > self.latency_blocker_percent:
            blockers.append(
                f"Significant latency regression: +{latency_delta:.0f}% "
                f"(threshold: {self.latency_blocker_percent:.0f}%)"
            )
        elif latency_delta > self.latency_warning_percent:
            warnings.append(
                f"Latency increased: +{latency_delta:.0f}% (consider optimization)"
            )

        # Check cost regression
        if summary.cost_stats is not None:
            cost_delta = summary.cost_stats.delta_percent
            if cost_delta > self.cost_blocker_percent:
                blockers.append(
                    f"Significant cost increase: +{cost_delta:.0f}% "
                    f"(threshold: {self.cost_blocker_percent:.0f}%)"
                )
            elif cost_delta > self.cost_warning_percent:
                warnings.append(
                    f"Cost increased: +{cost_delta:.0f}% (consider optimization)"
                )
        else:
            # Warn about incomplete cost data
            warnings.append(COST_NA_WARNING)

        # Check for new violations (non-critical)
        if violations.new_violations > 0 and violations.new_critical_violations == 0:
            warnings.append(
                f"{violations.new_violations} new non-critical violation(s) detected"
            )

        # Determine action based on logic
        has_critical = violations.new_critical_violations > 0
        has_blockers = len(blockers) > 0

        if (
            confidence >= self.confidence_approve_threshold
            and not has_critical
            and not has_blockers
        ):
            action: Literal["approve", "review", "reject"] = "approve"
            rationale = "High confidence score with no critical violations or blockers."
        elif confidence >= self.confidence_review_threshold and not has_critical:
            action = "review"
            rationale = (
                "Acceptable confidence but requires human review due to warnings."
            )
        else:
            action = "reject"
            if has_critical:
                rationale = "Critical violations detected that must be resolved."
            elif confidence < self.confidence_review_threshold:
                rationale = f"Confidence too low ({confidence:.0%}) for approval."
            else:
                rationale = "Blocking issues detected that must be resolved."

        # Generate next steps based on action
        if action == "approve":
            next_steps = [
                "Review the summary to confirm expected behavior",
                "Proceed with merge/deployment",
            ]
        elif action == "review":
            next_steps = [
                "Review warnings and assess risk",
                "Run additional targeted tests if needed",
                "Consider performance optimization if latency/cost increased",
                "Approve or request changes based on review",
            ]
        else:  # reject
            if has_critical:
                next_steps.append("Fix critical invariant violations")
            if summary.pass_rate < self.pass_rate_minimum:
                next_steps.append("Investigate and fix failing test cases")
            if latency_delta > self.latency_blocker_percent:
                next_steps.append("Optimize code to reduce latency regression")
            if (
                summary.cost_stats
                and summary.cost_stats.delta_percent > self.cost_blocker_percent
            ):
                next_steps.append("Optimize to reduce cost increase")
            next_steps.append("Re-run corpus replay after fixes")

        return ModelDecisionRecommendation(
            action=action,
            confidence=confidence,
            blockers=blockers,
            warnings=warnings,
            next_steps=next_steps,
            rationale=rationale,
        )


__all__ = ["ServiceDecisionReportGenerator"]
