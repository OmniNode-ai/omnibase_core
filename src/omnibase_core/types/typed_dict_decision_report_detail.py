"""TypedDict for decision report comparison detail (OMN-1199)."""

from typing import TypedDict


class TypedDictDecisionReportDetail(TypedDict):
    """Individual comparison detail in the decision report JSON structure."""

    comparison_id: str  # string-id-ok: UUID serialized as string for JSON output
    baseline_execution_id: str  # string-id-ok: UUID serialized for JSON output
    replay_execution_id: str  # string-id-ok: UUID serialized for JSON output
    input_hash: str
    input_hash_match: bool
    output_match: bool
    baseline_latency_ms: float
    replay_latency_ms: float
    latency_delta_ms: float
    latency_delta_percent: float
    baseline_cost: float | None
    replay_cost: float | None
    cost_delta: float | None
    cost_delta_percent: float | None
    compared_at: str


__all__ = ["TypedDictDecisionReportDetail"]
