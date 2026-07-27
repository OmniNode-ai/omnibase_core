# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Definition-B composite response model for the compliance-report REDUCER
node (OMN-14629).

Wraps the ``(new_state, intents[])`` tuple ``reduce_compliance`` returns into
a single typed BaseModel so the response is publishable by the runtime's
shared adapter (``omnibase_core.runtime.runtime_local_adapter``) without
being mistaken for a def-B fan-out sequence (OMN-14403 Sec6ii): the reducer
emits ONE state transition per invocation, not N independent events.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.compliance_report.model_compliance_report_state import (
    ModelComplianceReportState,
)
from omnibase_core.models.reducer.model_intent import ModelIntent

__all__ = ["ModelComplianceReportReduceResponse"]


class ModelComplianceReportReduceResponse(BaseModel):
    """Composite response: the new accumulated state + any emitted intents."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    state: ModelComplianceReportState
    intents: list[ModelIntent] = Field(default_factory=list)
