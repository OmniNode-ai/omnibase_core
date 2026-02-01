"""TypedDict for decision report summary section (OMN-1199)."""

from typing import TypedDict


class TypedDictDecisionReportSummary(TypedDict):
    """Summary section of the decision report JSON structure."""

    summary_id: str  # string-id-ok: UUID serialized as string for JSON output
    corpus_id: str  # string-id-ok: corpus identifier serialized as string
    baseline_version: str  # string-version-ok: version serialized for JSON
    replay_version: str  # string-version-ok: version serialized for JSON
    total_executions: int
    passed_count: int
    failed_count: int
    pass_rate: float
    confidence_score: float
    headline: str
    started_at: str
    ended_at: str


__all__ = ["TypedDictDecisionReportSummary"]
