"""TypedDict for top-level decision report JSON structure (OMN-1199)."""

from typing import NotRequired, TypedDict

from omnibase_core.types.typed_dict_decision_report_detail import (
    TypedDictDecisionReportDetail,
)
from omnibase_core.types.typed_dict_decision_report_performance import (
    TypedDictDecisionReportPerformance,
)
from omnibase_core.types.typed_dict_decision_report_recommendation import (
    TypedDictDecisionReportRecommendation,
)
from omnibase_core.types.typed_dict_decision_report_summary import (
    TypedDictDecisionReportSummary,
)
from omnibase_core.types.typed_dict_decision_report_violations import (
    TypedDictDecisionReportViolations,
)


class TypedDictDecisionReport(TypedDict):
    """Top-level decision report JSON structure."""

    report_version: str  # string-version-ok: version serialized for JSON output
    generated_at: str
    summary: TypedDictDecisionReportSummary
    violations: TypedDictDecisionReportViolations
    performance: TypedDictDecisionReportPerformance
    recommendation: TypedDictDecisionReportRecommendation
    details: NotRequired[list[TypedDictDecisionReportDetail]]


__all__ = ["TypedDictDecisionReport"]
