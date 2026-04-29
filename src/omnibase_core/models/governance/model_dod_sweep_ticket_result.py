# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDodSweepTicketResult — DoD compliance result for a single ticket."""

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.governance.enum_dod_sweep_check import EnumDodSweepCheck
from omnibase_core.enums.governance.enum_invariant_status import EnumInvariantStatus
from omnibase_core.models.governance.model_dod_sweep_check_result import (
    ModelDodSweepCheckResult,
)


class ModelDodSweepTicketResult(BaseModel):
    """DoD compliance result for a single ticket."""

    model_config = ConfigDict(frozen=True)
    expected_dod_checks: ClassVar[frozenset[EnumDodSweepCheck]] = frozenset(
        EnumDodSweepCheck
    )

    # string-id-ok: Linear ticket ID (e.g., OMN-1234), not a DB UUID
    ticket_id: str = Field(..., description="Linear ticket ID (e.g., OMN-1234)")
    title: str = Field(..., description="Ticket title from Linear")
    unknown_subtype: Literal[
        "exempt", "mixed_evidence", "no_evidence_backed_passes", None
    ] = Field(
        default=None,
        description="Structured subtype when overall_status is UNKNOWN",
    )
    completed_at: str | None = Field(
        default=None, description="ISO date when ticket was completed"
    )
    checks: list[ModelDodSweepCheckResult] = Field(
        ..., description="Results for all 6 DoD checks", min_length=6, max_length=6
    )
    overall_status: EnumInvariantStatus = Field(
        default=EnumInvariantStatus.UNKNOWN,
        description="Derived: FAIL if any check FAIL, PASS if all PASS.",
    )
    exempted: bool = Field(default=False, description="Whether this ticket is exempt")
    exemption_reason: str | None = Field(
        default=None, description="Why this ticket is exempt"
    )
    # string-id-ok: Linear follow-up ticket ID reference (e.g., OMN-1234), not a DB UUID
    follow_up_ticket_id: str | None = Field(
        default=None, description="Created follow-up ticket ID, if any"
    )

    @model_validator(mode="after")
    def derive_overall_status(self) -> "ModelDodSweepTicketResult":
        actual_checks = {check.check for check in self.checks}
        if actual_checks != self.expected_dod_checks:
            msg = "checks must contain each DoD check exactly once"
            raise ValueError(msg)

        if self.exempted and self.exemption_reason is None:
            msg = "exemption_reason is required when exempted is true"
            raise ValueError(msg)
        if not self.exempted and self.exemption_reason is not None:
            msg = "exemption_reason is only allowed when exempted is true"
            raise ValueError(msg)

        if self.exempted:
            object.__setattr__(self, "overall_status", EnumInvariantStatus.UNKNOWN)
            return self
        statuses = [c.status for c in self.checks]
        if not statuses:
            derived = EnumInvariantStatus.UNKNOWN
        elif any(s == EnumInvariantStatus.FAIL for s in statuses):
            derived = EnumInvariantStatus.FAIL
        elif all(s == EnumInvariantStatus.PASS for s in statuses):
            derived = EnumInvariantStatus.PASS
        else:
            derived = EnumInvariantStatus.UNKNOWN
        object.__setattr__(self, "overall_status", derived)
        return self
