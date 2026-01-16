"""TypedDict for decision report violations section (OMN-1199)."""

from typing import TypedDict


class TypedDictDecisionReportViolations(TypedDict):
    """Violations section of the decision report JSON structure."""

    total: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    new_violations: int
    new_critical_violations: int
    fixed_violations: int


__all__ = ["TypedDictDecisionReportViolations"]
