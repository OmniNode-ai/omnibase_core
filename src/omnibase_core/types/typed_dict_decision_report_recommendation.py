"""TypedDict for decision report recommendation section (OMN-1199)."""

from typing import Literal, TypedDict


class TypedDictDecisionReportRecommendation(TypedDict):
    """Recommendation section of the decision report JSON structure."""

    action: Literal["approve", "review", "reject"]
    confidence: float
    blockers: list[str]
    warnings: list[str]
    next_steps: list[str]
    rationale: str


__all__ = ["TypedDictDecisionReportRecommendation"]
