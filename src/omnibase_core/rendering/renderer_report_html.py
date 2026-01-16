"""HTML report renderer for evidence summaries (OMN-1200).

Renders evidence summaries to standalone HTML with inline CSS,
suitable for dashboards and web views.

Thread Safety:
    RendererReportHtml is stateless with only static methods. Thread-safe.
"""

import html as html_module
from datetime import UTC, datetime

from omnibase_core.models.evidence.model_decision_recommendation import (
    ModelDecisionRecommendation,
)
from omnibase_core.models.evidence.model_evidence_summary import ModelEvidenceSummary
from omnibase_core.models.replay.model_execution_comparison import (
    ModelExecutionComparison,
)

# Maximum comparison details to render in HTML before truncation
# (prevents DOM bloat for large corpus replays)
COMPARISON_DETAIL_LIMIT_HTML = 50

# UUID display truncation - shows first N characters for readability
UUID_DISPLAY_LENGTH = 8

# CSS color scheme - used for inline styles to ensure portability
CSS_COLORS = {
    "success": "#28a745",
    "warning": "#ffc107",
    "danger": "#dc3545",
    "info": "#17a2b8",
    "muted": "#6c757d",
    "bg_light": "#f8f9fa",
    "border": "#dee2e6",
}

# Severity sort order for HTML tables (lower value = higher priority in display)
SEVERITY_SORT_ORDER: dict[str, int] = {
    "critical": 0,
    "warning": 1,
    "info": 2,
}
DEFAULT_FALLBACK_SORT_ORDER = 99  # Unknown severities sort last


class RendererReportHtml:
    """Render evidence reports to HTML format.

    Generates standalone HTML with inline CSS for portability.
    All user content is escaped to prevent XSS.

    Thread Safety:
        All methods are static and stateless. Thread-safe.
    """

    @staticmethod
    def render(
        summary: ModelEvidenceSummary,
        comparisons: list[ModelExecutionComparison],
        recommendation: ModelDecisionRecommendation,
        include_details: bool = True,
        generated_at: datetime | None = None,
        standalone: bool = True,
    ) -> str:
        """Render evidence to HTML format.

        Args:
            summary: Evidence summary to render.
            comparisons: Individual comparisons for detail section.
            recommendation: Pre-generated recommendation.
            include_details: Whether to include comparison details.
            generated_at: Optional timestamp (defaults to now).
            standalone: If True, include full HTML document structure.
                       If False, return just the content div.

        Returns:
            HTML string with inline CSS.

        Raises:
            ValueError: If generated_at is provided but timezone-naive. All timestamps
                must be timezone-aware to ensure consistent RFC 3339 format output.
        """
        # Validate timezone-awareness for consistent timestamp format
        if generated_at is not None and generated_at.tzinfo is None:
            msg = "generated_at must be timezone-aware (e.g., datetime.now(tz=UTC))"
            # error-ok: ValueError for public API boundary validation per CLAUDE.md policy
            raise ValueError(msg)

        generated_at_str = (
            generated_at.isoformat()
            if generated_at
            else datetime.now(tz=UTC).isoformat()
        )

        # Build content sections
        content: list[str] = []
        content.append(RendererReportHtml._render_header(generated_at_str))
        content.append(RendererReportHtml._render_summary_section(summary))
        content.append(
            RendererReportHtml._render_recommendation_section(recommendation)
        )
        content.append(RendererReportHtml._render_violations_section(summary))
        content.append(RendererReportHtml._render_performance_section(summary))

        if include_details and comparisons:
            content.append(RendererReportHtml._render_details_section(comparisons))

        content.append(RendererReportHtml._render_footer())

        body = "\n".join(content)

        if standalone:
            return RendererReportHtml._wrap_standalone(body)
        return f'<div class="evidence-report">{body}</div>'

    @staticmethod
    def _get_styles() -> str:
        """Return inline CSS styles."""
        return """
        <style>
            .evidence-report { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }
            .evidence-report h1 { color: #333; border-bottom: 2px solid #dee2e6; padding-bottom: 10px; }
            .evidence-report h2 { color: #495057; margin-top: 30px; }
            .evidence-report table { width: 100%; border-collapse: collapse; margin: 15px 0; }
            .evidence-report th, .evidence-report td { padding: 10px; text-align: left; border: 1px solid #dee2e6; }
            .evidence-report th { background-color: #f8f9fa; font-weight: 600; }
            .evidence-report .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
            .evidence-report .badge-success { background-color: #d4edda; color: #155724; }
            .evidence-report .badge-warning { background-color: #fff3cd; color: #856404; }
            .evidence-report .badge-danger { background-color: #f8d7da; color: #721c24; }
            .evidence-report .metric-positive { color: #28a745; }
            .evidence-report .metric-negative { color: #dc3545; }
            .evidence-report .details-toggle { cursor: pointer; color: #007bff; }
            .evidence-report .muted { color: #6c757d; font-style: italic; }
            .evidence-report code { background-color: #f8f9fa; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
        </style>
        """

    @staticmethod
    def _wrap_standalone(body: str) -> str:
        """Wrap content in full HTML document."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Corpus Replay Evidence Report</title>
    {RendererReportHtml._get_styles()}
</head>
<body>
    <div class="evidence-report">
        {body}
    </div>
</body>
</html>"""

    @staticmethod
    def _render_header(generated_at: str) -> str:
        """Render report header."""
        return f"""
        <h1>Corpus Replay Evidence Report</h1>
        <p class="muted">Generated: {html_module.escape(generated_at)}</p>
        """

    @staticmethod
    def _render_summary_section(summary: ModelEvidenceSummary) -> str:
        """Render summary section."""
        pass_rate_pct = summary.pass_rate * 100
        confidence_pct = summary.confidence_score * 100
        return f"""
        <h2>Summary</h2>
        <p><strong>Corpus:</strong> <code>{html_module.escape(summary.corpus_id)}</code></p>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Baseline Version</td><td><code>{html_module.escape(summary.baseline_version)}</code></td></tr>
            <tr><td>Replay Version</td><td><code>{html_module.escape(summary.replay_version)}</code></td></tr>
            <tr><td>Pass Rate</td><td>{summary.passed_count}/{summary.total_executions} ({pass_rate_pct:.1f}%)</td></tr>
            <tr><td>Confidence</td><td>{confidence_pct:.1f}%</td></tr>
        </table>
        <p><strong>Headline:</strong> {html_module.escape(summary.headline)}</p>
        """

    @staticmethod
    def _render_recommendation_section(
        recommendation: ModelDecisionRecommendation,
    ) -> str:
        """Render recommendation section."""
        badge_class = {
            "approve": "badge-success",
            "review": "badge-warning",
            "reject": "badge-danger",
        }.get(recommendation.action, "badge-warning")

        lines: list[str] = [
            f"""
        <h2>Recommendation</h2>
        <p><span class="badge {badge_class}">{html_module.escape(recommendation.action.upper())}</span>
        (confidence: {recommendation.confidence:.0%})</p>
        """
        ]

        if recommendation.rationale:
            lines.append(
                f'<p class="muted">{html_module.escape(recommendation.rationale)}</p>'
            )

        if recommendation.blockers:
            lines.append("<h3>Blockers</h3><ul>")
            for blocker in recommendation.blockers:
                lines.append(
                    f'<li style="color: {CSS_COLORS["danger"]};">'
                    f"{html_module.escape(blocker)}</li>"
                )
            lines.append("</ul>")

        if recommendation.warnings:
            lines.append("<h3>Warnings</h3><ul>")
            for warning in recommendation.warnings:
                lines.append(
                    f'<li style="color: {CSS_COLORS["warning"]};">'
                    f"{html_module.escape(warning)}</li>"
                )
            lines.append("</ul>")

        if recommendation.next_steps:
            lines.append("<h3>Next Steps</h3><ol>")
            for step in recommendation.next_steps:
                lines.append(f"<li>{html_module.escape(step)}</li>")
            lines.append("</ol>")

        return "\n".join(lines)

    @staticmethod
    def _render_violations_section(summary: ModelEvidenceSummary) -> str:
        """Render invariant violations section."""
        violations = summary.invariant_violations
        if violations.total_violations == 0:
            return """
            <h2>Invariant Violations</h2>
            <p><span class="badge badge-success">No violations detected</span></p>
            """

        lines: list[str] = [
            f"""
        <h2>Invariant Violations</h2>
        <p><span class="badge badge-warning">{violations.total_violations} violation(s)</span>
        ({violations.new_violations} new, {violations.fixed_violations} fixed)</p>
        """
        ]

        if violations.by_type:
            lines.append("<h3>By Type</h3><table><tr><th>Type</th><th>Count</th></tr>")
            for vtype, count in sorted(violations.by_type.items()):
                lines.append(
                    f"<tr><td>{html_module.escape(vtype)}</td><td>{count}</td></tr>"
                )
            lines.append("</table>")

        # FIX(PR #391): Normalize severity keys to lowercase for case-insensitive
        # aggregation and consistent display. Input may have mixed case keys
        # ("CRITICAL", "Warning", "info"). Aggregate counts for same severity
        # with different cases, e.g., {"HIGH": 5, "High": 3} becomes {"high": 8}
        if violations.by_severity:
            lines.append(
                "<h3>By Severity</h3><table><tr><th>Severity</th><th>Count</th></tr>"
            )
            # Aggregate counts by normalized (lowercase) severity key
            aggregated: dict[str, int] = {}
            for severity, count in violations.by_severity.items():
                normalized_key = severity.lower()
                aggregated[normalized_key] = aggregated.get(normalized_key, 0) + count
            # Sort by priority: critical (0) > warning (1) > info (2) > unknown (99)
            for severity, count in sorted(
                aggregated.items(),
                key=lambda x: SEVERITY_SORT_ORDER.get(
                    x[0], DEFAULT_FALLBACK_SORT_ORDER
                ),
            ):
                # Capitalize severity for consistent display, escape for XSS prevention
                escaped_severity = html_module.escape(severity.capitalize())
                lines.append(f"<tr><td>{escaped_severity}</td><td>{count}</td></tr>")
            lines.append("</table>")

        return "\n".join(lines)

    @staticmethod
    def _render_performance_section(summary: ModelEvidenceSummary) -> str:
        """Render performance section."""
        latency = summary.latency_stats
        delta_class = (
            "metric-negative" if latency.delta_avg_percent > 0 else "metric-positive"
        )

        lines: list[str] = [
            f"""
        <h2>Performance</h2>
        <h3>Latency</h3>
        <p>Average latency change: <span class="{delta_class}">{latency.delta_avg_percent:+.1f}%</span></p>
        <table>
            <tr><th>Metric</th><th>Baseline</th><th>Replay</th><th>Delta</th></tr>
            <tr><td>Average</td><td>{latency.baseline_avg_ms:.1f}ms</td><td>{latency.replay_avg_ms:.1f}ms</td><td>{latency.delta_avg_ms:+.1f}ms</td></tr>
            <tr><td>P50</td><td>{latency.baseline_p50_ms:.1f}ms</td><td>{latency.replay_p50_ms:.1f}ms</td><td>{latency.delta_p50_percent:+.1f}%</td></tr>
            <tr><td>P95</td><td>{latency.baseline_p95_ms:.1f}ms</td><td>{latency.replay_p95_ms:.1f}ms</td><td>{latency.delta_p95_percent:+.1f}%</td></tr>
        </table>
        """
        ]

        lines.append("<h3>Cost</h3>")
        if summary.cost_stats is not None:
            cost = summary.cost_stats
            cost_class = (
                "metric-negative" if cost.delta_percent > 0 else "metric-positive"
            )
            lines.append(
                f"""
            <p>Total cost change: <span class="{cost_class}">{cost.delta_percent:+.1f}%</span></p>
            <table>
                <tr><th>Metric</th><th>Baseline</th><th>Replay</th><th>Delta</th></tr>
                <tr><td>Total</td><td>${cost.baseline_total:.4f}</td><td>${cost.replay_total:.4f}</td><td>${cost.delta_total:+.4f}</td></tr>
                <tr><td>Avg/Execution</td><td>${cost.baseline_avg_per_execution:.6f}</td><td>${cost.replay_avg_per_execution:.6f}</td><td>-</td></tr>
            </table>
            """
            )
        else:
            lines.append(
                '<p class="muted">Cost data not available (incomplete data)</p>'
            )

        return "\n".join(lines)

    @staticmethod
    def _render_details_section(
        comparisons: list[ModelExecutionComparison],
        limit: int = COMPARISON_DETAIL_LIMIT_HTML,
    ) -> str:
        """Render comparison details section."""
        lines: list[str] = [
            """
        <h2>Comparison Details</h2>
        <details>
            <summary class="details-toggle">Click to expand comparison details</summary>
            <table>
                <tr><th>Status</th><th>Comparison ID</th><th>Latency Delta</th><th>Output Match</th></tr>
        """
        ]

        for c in comparisons[:limit]:
            status_badge = "badge-success" if c.output_match else "badge-danger"
            status_text = "PASS" if c.output_match else "FAIL"
            # Truncate UUID to first 8 chars for display (safe even if shorter)
            comp_id = str(c.comparison_id)[:UUID_DISPLAY_LENGTH]
            lines.append(
                f"""
                <tr>
                    <td><span class="badge {status_badge}">{status_text}</span></td>
                    <td><code>{html_module.escape(comp_id)}...</code></td>
                    <td>{c.latency_delta_percent:+.1f}%</td>
                    <td>{"Yes" if c.output_match else "No"}</td>
                </tr>
            """
            )

        if len(comparisons) > limit:
            lines.append(
                f'<tr><td colspan="4" class="muted">... and {len(comparisons) - limit} more comparisons</td></tr>'
            )

        lines.append("</table></details>")
        return "\n".join(lines)

    @staticmethod
    def _render_footer() -> str:
        """Render report footer."""
        return '<hr><p class="muted">Report version: 1.0.0</p>'


__all__ = [
    "COMPARISON_DETAIL_LIMIT_HTML",
    "CSS_COLORS",
    "DEFAULT_FALLBACK_SORT_ORDER",
    "RendererReportHtml",
    "SEVERITY_SORT_ORDER",
    "UUID_DISPLAY_LENGTH",
]
