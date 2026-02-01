"""JSON report renderer for evidence summaries (OMN-1200).

Renders evidence summaries to structured JSON format suitable for
API responses, storage, or further processing.

Thread Safety:
    RendererReportJson is stateless with only static methods. Thread-safe.

.. versionadded:: 0.6.5
    Extracted from ServiceDecisionReportGenerator as part of OMN-1200.
"""

import json
from datetime import UTC, datetime

from omnibase_core.models.evidence.model_decision_recommendation import (
    ModelDecisionRecommendation,
)
from omnibase_core.models.evidence.model_evidence_summary import ModelEvidenceSummary
from omnibase_core.models.replay.model_execution_comparison import (
    ModelExecutionComparison,
)
from omnibase_core.types.typed_dict_decision_report import TypedDictDecisionReport

# Report version constant (semantic versioning)
# string-version-ok: plain str for TypedDict compatibility
REPORT_VERSION: str = "1.0.0"

# JSON formatting
JSON_INDENT_SPACES = 2


class RendererReportJson:
    """Render evidence reports to JSON format.

    This class provides static methods to render ModelEvidenceSummary and
    ModelExecutionComparison data into JSON-serializable dictionaries and
    JSON strings suitable for API responses, storage, or further processing.

    All methods are static and stateless, making RendererReportJson thread-safe
    for concurrent use from multiple threads.

    Example:
        >>> from omnibase_core.rendering import RendererReportJson
        >>>
        >>> # Render evidence to JSON structure
        >>> report = RendererReportJson.render(
        ...     summary=summary,
        ...     comparisons=comparisons,
        ...     recommendation=recommendation,
        ... )
        >>>
        >>> # Serialize to JSON string
        >>> json_str = RendererReportJson.serialize(report)

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
        include_details: bool = False,
        generated_at: datetime | None = None,
    ) -> TypedDictDecisionReport:
        """Render evidence to JSON format.

        Creates a JSON-serializable dictionary with all evidence data suitable
        for API responses, storage, or further processing. Output is deterministic
        when a fixed `generated_at` timestamp is provided.

        Args:
            summary: Aggregated evidence summary from corpus replay.
            comparisons: Individual execution comparisons.
            recommendation: Decision recommendation to include in report.
            include_details: Whether to include individual comparison details.
            generated_at: Optional timestamp for report generation. If None, uses
                current UTC time. Providing a fixed timestamp enables deterministic
                output for testing.

        Returns:
            TypedDictDecisionReport with report data.

        Raises:
            ValueError: If generated_at is provided but timezone-naive. All timestamps
                must be timezone-aware to ensure consistent RFC 3339 format output.

        Example:
            >>> report = RendererReportJson.render(
            ...     summary, comparisons, recommendation
            ... )
            >>> json_str = json.dumps(report, sort_keys=True)
        """
        # Validate timezone-awareness for consistent timestamp format
        if generated_at is not None and generated_at.tzinfo is None:
            msg = "generated_at must be timezone-aware (e.g., datetime.now(tz=UTC))"
            # error-ok: ValueError for public API boundary validation per CLAUDE.md policy
            raise ValueError(msg)

        report: TypedDictDecisionReport = {
            "report_version": REPORT_VERSION,
            "generated_at": generated_at.isoformat()
            if generated_at
            else datetime.now(tz=UTC).isoformat(),
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

    @staticmethod
    def serialize(report: TypedDictDecisionReport) -> str:
        """Serialize JSON report to string.

        The report from render() is guaranteed to be JSON-serializable without
        custom type converters - all datetimes are pre-converted to ISO strings.

        Args:
            report: The typed dict report to serialize.

        Returns:
            JSON string representation of the report with unicode preserved.

        Raises:
            TypeError: If report contains non-serializable types (indicates a bug
                in render() - all values should already be JSON-native types).

        Example:
            >>> report = RendererReportJson.render(summary, comparisons, recommendation)
            >>> json_str = RendererReportJson.serialize(report)
        """
        return json.dumps(report, indent=JSON_INDENT_SPACES, ensure_ascii=False)


__all__ = [
    "JSON_INDENT_SPACES",
    "REPORT_VERSION",
    "RendererReportJson",
]
