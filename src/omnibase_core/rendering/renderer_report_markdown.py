"""Markdown report renderer for evidence summaries (OMN-1200).

Renders evidence summaries to GitHub-flavored markdown suitable for
pull request descriptions and documentation.

Thread Safety:
    RendererReportMarkdown is stateless with only static methods. Thread-safe.

.. versionadded:: 0.6.5
    Extracted from ServiceDecisionReportGenerator as part of OMN-1200.
"""

from datetime import UTC, datetime

from omnibase_core.models.evidence.model_decision_recommendation import (
    ModelDecisionRecommendation,
)
from omnibase_core.models.evidence.model_evidence_summary import ModelEvidenceSummary
from omnibase_core.models.replay.model_execution_comparison import (
    ModelExecutionComparison,
)

# Module constants - comparison display limits
# Markdown allows higher limit than CLI due to collapsible sections
COMPARISON_LIMIT_MARKDOWN = 50

# UUID display truncation - shows first N characters for readability while
# maintaining enough uniqueness for visual identification in tables
UUID_DISPLAY_LENGTH = 8

# Severity sort order for markdown tables (lower value = higher priority in display)
SEVERITY_SORT_ORDER: dict[str, int] = {
    "critical": 0,
    "warning": 1,
    "info": 2,
}
DEFAULT_FALLBACK_SORT_ORDER = 99  # Unknown severities sort last

# Cost data unavailability message for markdown format
COST_NA_MARKDOWN = "_Cost data not available (incomplete data)_"

# Report version for footer
REPORT_VERSION = "1.0.0"

# Characters that need escaping in markdown table cells
# These could break table formatting or create unintended formatting
# Order matters: backslash must be escaped first to avoid double-escaping
MARKDOWN_ESCAPE_CHARS = (
    ("\\", r"\\"),  # Backslash - must be first to avoid double-escaping
    ("|", r"\|"),  # Table cell delimiter
    ("*", r"\*"),  # Emphasis
    ("_", r"\_"),  # Emphasis
    ("`", r"\`"),  # Code
    ("[", r"\["),  # Links
    ("]", r"\]"),  # Links
    ("\n", " "),  # Newlines break table rows
    ("\r", ""),  # Remove carriage returns
)


def escape_markdown(text: str) -> str:
    """Escape markdown-sensitive characters in text content.

    Escapes characters that could break table formatting or create
    unintended emphasis/links in markdown content. Safe for use in
    table cells, emphasis, and general text.

    Args:
        text: Raw text content to escape.

    Returns:
        Text with markdown-sensitive characters escaped.

    Example:
        >>> escape_markdown("value|with*special_chars")
        'value\\|with\\*special\\_chars'
        >>> escape_markdown("path\\to\\file")
        'path\\\\to\\\\file'
    """
    result = text
    for char, replacement in MARKDOWN_ESCAPE_CHARS:
        result = result.replace(char, replacement)
    return result


class RendererReportMarkdown:
    """Render evidence reports to Markdown format.

    This class provides static methods to render ModelEvidenceSummary instances
    into GitHub-flavored markdown for pull request descriptions, documentation,
    or other markdown-rendering contexts.

    All methods are static and stateless, making RendererReportMarkdown thread-safe
    for concurrent use from multiple threads.

    Example:
        >>> from omnibase_core.rendering import RendererReportMarkdown
        >>> from omnibase_core.models.evidence import (
        ...     ModelEvidenceSummary,
        ...     ModelDecisionRecommendation,
        ... )
        >>>
        >>> # Render evidence to markdown
        >>> markdown = RendererReportMarkdown.render(
        ...     summary=summary,
        ...     comparisons=comparisons,
        ...     recommendation=recommendation,
        ... )
        >>>
        >>> # Save to file
        >>> with open("report.md", "w") as f:
        ...     f.write(markdown)

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
        include_details: bool = True,
        generated_at: datetime | None = None,
        latency_warning_threshold: float = 20.0,
        cost_warning_threshold: float = 20.0,
    ) -> str:
        """Render evidence to Markdown format.

        Creates GitHub-flavored markdown suitable for pull request descriptions,
        documentation, or other markdown-rendering contexts.

        Args:
            summary: Aggregated evidence summary from corpus replay.
            comparisons: Individual execution comparisons.
            recommendation: Pre-generated recommendation for the evidence.
            include_details: Whether to include individual comparison details.
            generated_at: Optional timestamp for report generation. If None, uses
                current UTC time. Providing a fixed timestamp enables deterministic
                output for testing.
            latency_warning_threshold: Threshold percentage for latency warning emoji.
                Values above this threshold display a warning emoji.
            cost_warning_threshold: Threshold percentage for cost warning emoji.
                Values above this threshold display a warning emoji.

        Returns:
            GitHub-flavored markdown string.

        Raises:
            ValueError: If generated_at is provided but timezone-naive. All timestamps
                must be timezone-aware to ensure consistent RFC 3339 format output.

        Example:
            >>> md_report = RendererReportMarkdown.render(
            ...     summary, comparisons, recommendation
            ... )
            >>> with open("report.md", "w") as f:
            ...     f.write(md_report)
        """
        # Validate timezone-awareness for consistent timestamp format
        if generated_at is not None and generated_at.tzinfo is None:
            msg = "generated_at must be timezone-aware (e.g., datetime.now(tz=UTC))"
            # error-ok: ValueError for public API boundary validation per CLAUDE.md policy
            raise ValueError(msg)

        lines: list[str] = []

        # Header
        lines.append("# Corpus Replay Evidence Report")
        lines.append("")
        generated_at_str = (
            generated_at.isoformat()
            if generated_at
            else datetime.now(tz=UTC).isoformat()
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
        lines.append(f"**Headline**: {escape_markdown(summary.headline)}")
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
            lines.append(f"_{escape_markdown(recommendation.rationale)}_")
            lines.append("")

        if recommendation.blockers:
            lines.append("### Blockers")
            lines.append("")
            for blocker in recommendation.blockers:
                lines.append(f"- :x: {escape_markdown(blocker)}")
            lines.append("")

        if recommendation.warnings:
            lines.append("### Warnings")
            lines.append("")
            for warning in recommendation.warnings:
                lines.append(f"- :warning: {escape_markdown(warning)}")
            lines.append("")

        if recommendation.next_steps:
            lines.append("### Next Steps")
            lines.append("")
            for i, step in enumerate(recommendation.next_steps, 1):
                lines.append(f"{i}. {escape_markdown(step)}")
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
                    # Escape markdown-sensitive characters in type names
                    escaped_type = escape_markdown(vtype)
                    lines.append(f"| {escaped_type} | {count} |")
                lines.append("")

            # Violations by severity table
            # FIX: Violation severity display logic (PR #368) - Normalize severity keys
            # to lowercase for case-insensitive sorting and consistent display.
            # Input may have mixed case keys ("CRITICAL", "Warning", "info").
            # FIX(PR #391): Aggregate counts for same severity with different cases
            # e.g., {"HIGH": 5, "High": 3, "high": 2} becomes {"high": 10}
            if summary.invariant_violations.by_severity:
                lines.append("### By Severity")
                lines.append("")
                lines.append("| Severity | Count |")
                lines.append("|----------|-------|")
                # Aggregate counts by normalized (lowercase) severity key
                # This ensures "CRITICAL", "Critical", and "critical" sum to single row
                aggregated: dict[str, int] = {}
                for severity, count in summary.invariant_violations.by_severity.items():
                    normalized_key = severity.lower()
                    aggregated[normalized_key] = (
                        aggregated.get(normalized_key, 0) + count
                    )
                # Sort by priority: critical (0) > warning (1) > info (2) > unknown (99)
                for severity, count in sorted(
                    aggregated.items(),
                    key=lambda x: SEVERITY_SORT_ORDER.get(
                        x[0], DEFAULT_FALLBACK_SORT_ORDER
                    ),
                ):
                    # Capitalize severity for consistent display (e.g., "Critical")
                    lines.append(f"| {severity.capitalize()} | {count} |")
                lines.append("")

        # Performance section
        lines.append("## Performance")
        lines.append("")

        # Latency table
        lines.append("### Latency")
        lines.append("")
        latency = summary.latency_stats
        latency_emoji = (
            ":white_check_mark:"
            if latency.delta_avg_percent <= latency_warning_threshold
            else ":warning:"
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
                ":white_check_mark:"
                if cost.delta_percent <= cost_warning_threshold
                else ":warning:"
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
                    f"| {status} | `{str(c.comparison_id)[:UUID_DISPLAY_LENGTH]}...` | "
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


__all__ = [
    "COMPARISON_LIMIT_MARKDOWN",
    "COST_NA_MARKDOWN",
    "DEFAULT_FALLBACK_SORT_ORDER",
    "MARKDOWN_ESCAPE_CHARS",
    "REPORT_VERSION",
    "RendererReportMarkdown",
    "SEVERITY_SORT_ORDER",
    "UUID_DISPLAY_LENGTH",
    "escape_markdown",
]
