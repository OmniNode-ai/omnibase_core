# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Definition-B composite request model for the compliance-report REDUCER
node (OMN-14629).

A pure reducer's signature is ``delta(state, event) -> (new_state,
intents[])`` — two positional arguments in, a tuple out. Neither shape is
directly def-B adaptable (``handle(request) -> response`` takes exactly one
typed parameter). This model composes the prior accumulated state and the
new per-node check result into a single typed request so
``NodeComplianceReportReducer.handle()`` has one adaptable parameter while
``reduce_compliance`` (the pure function underneath) is untouched.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.compliance_report.model_compliance_check_result import (
    ModelComplianceCheckResult,
)
from omnibase_core.models.nodes.compliance_report.model_compliance_report_state import (
    ModelComplianceReportState,
)

__all__ = ["ModelComplianceReportReduceRequest"]


class ModelComplianceReportReduceRequest(BaseModel):
    """Composite request: prior state + the new check result to accumulate."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    state: ModelComplianceReportState
    check_result: ModelComplianceCheckResult
