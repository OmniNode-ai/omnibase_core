# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Report of the handler-contract compliance check."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_compliance_verdict import (
    EnumComplianceVerdict,
)
from omnibase_core.models.governance.model_handler_compliance_result import (
    ModelHandlerComplianceResult,
)

__all__ = ["ModelHandlerContractComplianceReport"]


class ModelHandlerContractComplianceReport(BaseModel):
    """One compliance result per handler file, in audit order."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    results: list[ModelHandlerComplianceResult] = Field(default_factory=list)

    @property
    def total(self) -> int:
        """Number of handlers audited."""
        return len(self.results)

    @property
    def new_violations(self) -> list[ModelHandlerComplianceResult]:
        """Results that carry a violation and are not allowlisted."""
        return [r for r in self.results if r.violations and not r.allowlisted]

    @property
    def compliant_count(self) -> int:
        """Results with no violation and a COMPLIANT verdict."""
        return sum(
            1
            for r in self.results
            if not r.violations and r.verdict == EnumComplianceVerdict.COMPLIANT
        )

    @property
    def allowlisted_count(self) -> int:
        """Results that are allowlisted."""
        return sum(1 for r in self.results if r.allowlisted)
