"""CLI report renderer for evidence summaries (OMN-1200).

Renders evidence summaries and recommendations to formatted terminal output
with configurable verbosity levels.

Thread Safety:
    RendererReportCli is stateless with only static methods. Thread-safe.

.. versionadded:: 0.6.5
    Extracted from ServiceDecisionReportGenerator as part of OMN-1200 refactoring.
"""

from typing import Literal

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.evidence.model_decision_recommendation import (
    ModelDecisionRecommendation,
)
from omnibase_core.models.evidence.model_evidence_summary import ModelEvidenceSummary
from omnibase_core.models.replay.model_execution_comparison import (
    ModelExecutionComparison,
)

# Report formatting constants
REPORT_WIDTH = 80
SEPARATOR_CHAR = "="
SEPARATOR_LINE = SEPARATOR_CHAR * REPORT_WIDTH
SUBSECTION_CHAR = "-"

# Comparison display limits - prevent terminal overflow in verbose mode
# while showing enough data for debugging
COMPARISON_LIMIT_CLI_VERBOSE = 10

# Percentage conversion multiplier (ratio 0.0-1.0 to percent 0-100)
PERCENTAGE_MULTIPLIER = 100

# Text truncation constants
ELLIPSIS = "..."
ELLIPSIS_LENGTH = len(ELLIPSIS)  # 3 characters for "..."

# UUID display truncation - shows first N characters for readability while
# maintaining enough uniqueness for visual identification in tables
UUID_DISPLAY_LENGTH = 8

# Cost data unavailability message for CLI format
COST_NA_CLI = "Cost:     N/A (incomplete cost data)"

# Maximum length for content within formatted lines (accounts for prefixes/formatting)
# For lines like "Corpus: {id}", we reserve space for the label
MAX_CONTENT_LENGTH = REPORT_WIDTH - ELLIPSIS_LENGTH


class RendererReportCli:
    """Render evidence reports to CLI format.

    This renderer transforms ModelEvidenceSummary and ModelExecutionComparison data
    into fixed-width (80 character) formatted reports suitable for terminal display.

    Supported verbosity levels:
        - "minimal": Headline and recommendation only
        - "standard": Full summary with sections
        - "verbose": Everything including comparison details

    All methods are static and stateless, making RendererReportCli thread-safe
    for concurrent use from multiple threads.

    Example:
        >>> from omnibase_core.rendering import RendererReportCli
        >>>
        >>> # Render standard report
        >>> report = RendererReportCli.render(summary, comparisons, recommendation)
        >>> print(report)
        >>>
        >>> # Render minimal output
        >>> minimal = RendererReportCli.render_minimal(summary, recommendation)
        >>> print(minimal)

    Thread Safety:
        All methods are static and stateless. Thread-safe.

    .. versionadded:: 0.6.5
        Extracted from ServiceDecisionReportGenerator as part of OMN-1200.
    """

    @staticmethod
    def render(
        summary: ModelEvidenceSummary,
        comparisons: list[ModelExecutionComparison],
        recommendation: ModelDecisionRecommendation,
        verbosity: Literal["minimal", "standard", "verbose"] = "standard",
    ) -> str:
        """Render evidence to CLI format.

        Creates a fixed-width (80 character) formatted report suitable for
        terminal output with configurable verbosity levels.

        Args:
            summary: Aggregated evidence summary from corpus replay.
            comparisons: Individual execution comparisons (used in verbose mode).
            recommendation: Decision recommendation with action, blockers, and warnings.
            verbosity: Output detail level:
                - "minimal": Headline and recommendation only
                - "standard": Full summary with sections
                - "verbose": Everything including comparison details

        Returns:
            Formatted string report for terminal display.

        Raises:
            ModelOnexError: If comparisons is not a list.

        Example:
            >>> report = RendererReportCli.render(summary, [], recommendation)
            >>> print(report)
        """
        # Validate comparisons input
        if not isinstance(comparisons, list):
            raise ModelOnexError(
                message="comparisons must be a list",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"comparisons_type": type(comparisons).__name__},
            )

        lines: list[str] = []

        if verbosity == "minimal":
            return RendererReportCli.render_minimal(summary, recommendation)

        # Header
        lines.append(SEPARATOR_LINE)
        lines.append(RendererReportCli._center_text("CORPUS REPLAY EVIDENCE REPORT"))
        lines.append(SEPARATOR_LINE)
        lines.append("")

        # Summary section
        RendererReportCli._format_section_header("SUMMARY", lines)
        lines.append(RendererReportCli._truncate_line(f"Corpus: {summary.corpus_id}"))
        lines.append(
            RendererReportCli._truncate_line(
                f"Baseline: {summary.baseline_version} | Replay: {summary.replay_version}"
            )
        )
        pass_rate_pct = summary.pass_rate * PERCENTAGE_MULTIPLIER
        lines.append(
            RendererReportCli._truncate_line(
                f"Executions: {summary.passed_count}/{summary.total_executions} "
                f"passed ({pass_rate_pct:.0f}%)"
            )
        )
        lines.append("")

        # Invariant violations section
        violation_count = summary.invariant_violations.total_violations
        RendererReportCli._format_section_header(
            f"INVARIANT VIOLATIONS ({violation_count})", lines
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
            #
            # FIX: Violation severity display logic (PR #368, PR #391) - Normalize severity
            # keys to lowercase for case-insensitive lookup. Input data may have severity
            # keys in any case (e.g., "CRITICAL", "Warning", "info"), but we need consistent
            # display. SUM counts for duplicate keys (e.g., "HIGH" + "High" + "high" = total).
            # Using dict comprehension would overwrite, so we iterate and accumulate.
            normalized_severity: dict[str, int] = {}
            for key, count in by_severity.items():
                normalized_key = key.lower()
                normalized_severity[normalized_key] = (
                    normalized_severity.get(normalized_key, 0) + count
                )
            severity_parts = []
            # Extract counts for each known severity level using normalized keys
            critical_count = normalized_severity.get("critical", 0)
            warning_count = normalized_severity.get("warning", 0)
            info_count = normalized_severity.get("info", 0)

            if critical_count > 0:
                severity_parts.append(f"{critical_count} critical")
            if warning_count > 0:
                severity_parts.append(f"{warning_count} warning")
            if verbosity == "verbose" and info_count > 0:
                severity_parts.append(f"{info_count} info")

            if severity_parts:
                lines.append(
                    RendererReportCli._truncate_line(
                        f"Severity: {', '.join(severity_parts)}"
                    )
                )

            # Show type breakdown without severity labels
            # (types and severities are independent aggregations)
            if by_type:
                lines.append("By type:")
                for violation_type, count in sorted(by_type.items()):
                    lines.append(
                        RendererReportCli._truncate_line(
                            f"  - {violation_type}: {count} violation(s)"
                        )
                    )

        lines.append("")

        # Performance section
        RendererReportCli._format_section_header("PERFORMANCE", lines)

        latency_delta = summary.latency_stats.delta_avg_percent
        latency_sign = "+" if latency_delta > 0 else ""
        baseline_latency = summary.latency_stats.baseline_avg_ms
        replay_latency = summary.latency_stats.replay_avg_ms
        lines.append(
            RendererReportCli._truncate_line(
                f"Latency:  {latency_sign}{latency_delta:.0f}% "
                f"(avg {baseline_latency:.0f}ms -> {replay_latency:.0f}ms)"
            )
        )

        if summary.cost_stats is not None:
            cost_delta = summary.cost_stats.delta_percent
            cost_sign = "+" if cost_delta > 0 else ""
            baseline_cost = summary.cost_stats.baseline_avg_per_execution
            replay_cost = summary.cost_stats.replay_avg_per_execution
            lines.append(
                RendererReportCli._truncate_line(
                    f"Cost:     {cost_sign}{cost_delta:.0f}% "
                    f"(${baseline_cost:.4f} -> ${replay_cost:.4f} per execution)"
                )
            )
        else:
            lines.append(COST_NA_CLI)

        lines.append("")

        # Recommendation section
        action_upper = recommendation.action.upper()
        RendererReportCli._format_section_header(
            f"RECOMMENDATION: {action_upper}", lines
        )
        lines.append(
            RendererReportCli._truncate_line(
                f"Confidence: {recommendation.confidence:.0%}"
            )
        )
        lines.append("")

        if recommendation.blockers:
            lines.append("Blockers:")
            for blocker in recommendation.blockers:
                lines.append(RendererReportCli._truncate_line(f"  - {blocker}"))
            lines.append("")

        if recommendation.warnings:
            lines.append("Warnings:")
            for warning in recommendation.warnings:
                lines.append(RendererReportCli._truncate_line(f"  - {warning}"))
            lines.append("")

        if recommendation.next_steps:
            lines.append("Next Steps:")
            for i, step in enumerate(recommendation.next_steps, 1):
                lines.append(RendererReportCli._truncate_line(f"  {i}. {step}"))
            lines.append("")

        # Verbose: include comparison details
        if verbosity == "verbose" and comparisons:
            RendererReportCli._format_section_header("COMPARISON DETAILS", lines)
            for comparison in comparisons[:COMPARISON_LIMIT_CLI_VERBOSE]:
                status = "PASS" if comparison.output_match else "FAIL"
                lines.append(
                    RendererReportCli._truncate_line(
                        f"[{status}] {comparison.comparison_id} | "
                        f"Latency: {comparison.latency_delta_percent:+.1f}%"
                    )
                )
            if len(comparisons) > COMPARISON_LIMIT_CLI_VERBOSE:
                lines.append(
                    f"... and {len(comparisons) - COMPARISON_LIMIT_CLI_VERBOSE} more comparisons"
                )
            lines.append("")

        lines.append(SEPARATOR_LINE)

        return "\n".join(lines)

    @staticmethod
    def render_minimal(
        summary: ModelEvidenceSummary,
        recommendation: ModelDecisionRecommendation,
    ) -> str:
        """Render minimal CLI output (headline + recommendation only).

        Args:
            summary: Aggregated evidence summary.
            recommendation: Decision recommendation with action and confidence.

        Returns:
            Minimal formatted report string.

        Example:
            >>> minimal = RendererReportCli.render_minimal(summary, recommendation)
            >>> print(minimal)
            100% pass rate | Baseline: v1.0.0 | Replay: v2.0.0
            Recommendation: APPROVE (confidence: 95%)
        """
        lines = [
            RendererReportCli._truncate_line(summary.headline),
            RendererReportCli._truncate_line(
                f"Recommendation: {recommendation.action.upper()} "
                f"(confidence: {recommendation.confidence:.0%})"
            ),
        ]
        return "\n".join(lines)

    @staticmethod
    def _center_text(text: str) -> str:
        """Center text within REPORT_WIDTH, truncating if necessary.

        Args:
            text: Text to center.

        Returns:
            Centered text string, truncated with ellipsis if too long.
        """
        # FIX: Off-by-one error (PR #368) - Use strict '>' comparison, not '>='.
        # Text of EXACTLY REPORT_WIDTH chars should NOT be truncated, only text
        # that is LONGER than REPORT_WIDTH. Using '>=' would incorrectly truncate
        # text that fits perfectly within the report width.
        if len(text) > REPORT_WIDTH:
            return text[: REPORT_WIDTH - ELLIPSIS_LENGTH] + ELLIPSIS
        # Text exactly REPORT_WIDTH chars - return as-is without centering
        if len(text) == REPORT_WIDTH:
            return text
        return text.center(REPORT_WIDTH)

    @staticmethod
    def _format_section_header(header: str, lines: list[str]) -> None:
        """Add a section header with matching underline to the lines list.

        This helper ensures consistent formatting of section headers in CLI reports
        and eliminates duplication of header text when calculating underline length.

        Args:
            header: The section header text.
            lines: The list of lines to append to (modified in place).
        """
        lines.append(header)
        # FIX: Underline length calculation (PR #368) - Use len(header) to ensure
        # the underline matches the header text length EXACTLY. Previously there
        # was a risk of inconsistency when the header string was duplicated in
        # both the header line and underline length calculation.
        lines.append(SUBSECTION_CHAR * len(header))

    @staticmethod
    def _truncate_line(line: str, max_width: int = REPORT_WIDTH) -> str:
        """Truncate a line to fit within max_width, adding ellipsis if needed.

        Args:
            line: The line to truncate.
            max_width: Maximum allowed width (default: REPORT_WIDTH).

        Returns:
            Line truncated with ellipsis if it exceeds max_width, otherwise unchanged.
        """
        if len(line) <= max_width:
            return line
        return line[: max_width - ELLIPSIS_LENGTH] + ELLIPSIS


__all__ = [
    "COMPARISON_LIMIT_CLI_VERBOSE",
    "COST_NA_CLI",
    "ELLIPSIS",
    "ELLIPSIS_LENGTH",
    "MAX_CONTENT_LENGTH",
    "PERCENTAGE_MULTIPLIER",
    "REPORT_WIDTH",
    "RendererReportCli",
    "SEPARATOR_CHAR",
    "SEPARATOR_LINE",
    "SUBSECTION_CHAR",
    "UUID_DISPLAY_LENGTH",
]
