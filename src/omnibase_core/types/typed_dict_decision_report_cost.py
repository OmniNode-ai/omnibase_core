"""TypedDict for decision report cost metrics (OMN-1199)."""

from typing import TypedDict


class TypedDictDecisionReportCost(TypedDict):
    """Cost metrics in the decision report performance section (optional)."""

    baseline_total: float
    replay_total: float
    delta_total: float
    delta_percent: float
    baseline_avg_per_execution: float
    replay_avg_per_execution: float


__all__ = ["TypedDictDecisionReportCost"]
