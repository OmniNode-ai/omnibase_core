"""TypedDict for decision report latency metrics (OMN-1199)."""

from typing import TypedDict


class TypedDictDecisionReportLatency(TypedDict):
    """Latency metrics in the decision report performance section."""

    baseline_avg_ms: float
    replay_avg_ms: float
    delta_avg_ms: float
    delta_avg_percent: float
    baseline_p50_ms: float
    replay_p50_ms: float
    delta_p50_percent: float
    baseline_p95_ms: float
    replay_p95_ms: float
    delta_p95_percent: float


__all__ = ["TypedDictDecisionReportLatency"]
