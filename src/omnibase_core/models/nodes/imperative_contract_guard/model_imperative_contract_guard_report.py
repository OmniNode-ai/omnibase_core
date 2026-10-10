# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Report of the imperative contract guard."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_compliance_verdict import EnumComplianceVerdict
from omnibase_core.enums.governance.enum_reachability import EnumReachability
from omnibase_core.models.governance.model_freestanding_imperative_result import (
    ModelFreestandingImperativeResult,
)
from omnibase_core.models.governance.model_handler_compliance_result import (
    ModelHandlerComplianceResult,
)

__all__ = ["ModelImperativeContractGuardReport"]


class ModelImperativeContractGuardReport(BaseModel):
    """Node results and freestanding results of one repository scan."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node_count: int = Field(default=0, ge=0)
    results: list[ModelHandlerComplianceResult] = Field(default_factory=list)
    freestanding_scanned: bool = False
    freestanding_module_count: int = Field(default=0, ge=0)
    freestanding_results: list[ModelFreestandingImperativeResult] = Field(
        default_factory=list
    )

    @property
    def blocking_results(self) -> list[ModelHandlerComplianceResult]:
        """Node results with a violation, not allowlisted, on live code."""
        return [
            r
            for r in self.results
            if r.violations
            and not r.allowlisted
            and r.reachability == EnumReachability.LIVE
        ]

    @property
    def non_live_results(self) -> list[ModelHandlerComplianceResult]:
        """Node results with a violation, not allowlisted, on code that is not live."""
        return [
            r
            for r in self.results
            if r.violations
            and not r.allowlisted
            and r.reachability != EnumReachability.LIVE
        ]

    @property
    def blocking_freestanding(self) -> list[ModelFreestandingImperativeResult]:
        """Freestanding results with a violation, not allowlisted, on live code."""
        return [
            r
            for r in self.freestanding_results
            if r.violations
            and not r.allowlisted
            and r.reachability == EnumReachability.LIVE
        ]

    @property
    def non_live_freestanding(self) -> list[ModelFreestandingImperativeResult]:
        """Freestanding results with a violation, not allowlisted, off live code."""
        return [
            r
            for r in self.freestanding_results
            if r.violations
            and not r.allowlisted
            and r.reachability != EnumReachability.LIVE
        ]

    @property
    def new_violation_count(self) -> int:
        """Blocking live violations, node and freestanding."""
        return len(self.blocking_results) + len(self.blocking_freestanding)

    @property
    def non_live_violation_count(self) -> int:
        """Reported violations that are not on live code."""
        return len(self.non_live_results) + len(self.non_live_freestanding)

    @property
    def compliant_count(self) -> int:
        """Node results with no violation and a COMPLIANT verdict."""
        return sum(
            1
            for r in self.results
            if not r.violations and r.verdict == EnumComplianceVerdict.COMPLIANT
        )

    @property
    def allowlisted_count(self) -> int:
        """Allowlisted node results plus allowlisted freestanding results."""
        return sum(1 for r in self.results if r.allowlisted) + sum(
            1 for r in self.freestanding_results if r.allowlisted
        )
