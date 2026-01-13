# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""TypedDict for decision report performance section (OMN-1199)."""

from typing import TypedDict

from omnibase_core.types.typed_dict_decision_report_cost import (
    TypedDictDecisionReportCost,
)
from omnibase_core.types.typed_dict_decision_report_latency import (
    TypedDictDecisionReportLatency,
)


class TypedDictDecisionReportPerformance(TypedDict):
    """Performance section of the decision report JSON structure."""

    latency: TypedDictDecisionReportLatency
    cost: TypedDictDecisionReportCost | None


__all__ = ["TypedDictDecisionReportPerformance"]
