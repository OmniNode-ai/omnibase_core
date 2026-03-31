# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Compliance report reducer node.

Pure reducer that accumulates per-node compliance check results into
an aggregate report with run identity and replace-on-duplicate semantics.

.. versionadded:: OMN-7070
"""

from omnibase_core.models.nodes.compliance_report.model_compliance_check_detail import (
    ModelComplianceCheckDetail,
)
from omnibase_core.models.nodes.compliance_report.model_compliance_check_result import (
    ModelComplianceCheckResult,
)
from omnibase_core.models.nodes.compliance_report.model_compliance_report_state import (
    ModelComplianceReportState,
)
from omnibase_core.nodes.node_compliance_report_reducer.handler import (
    NodeComplianceReportReducer,
    reduce_compliance,
)

__all__ = [
    "NodeComplianceReportReducer",
    "ModelComplianceCheckDetail",
    "ModelComplianceCheckResult",
    "ModelComplianceReportState",
    "reduce_compliance",
]
