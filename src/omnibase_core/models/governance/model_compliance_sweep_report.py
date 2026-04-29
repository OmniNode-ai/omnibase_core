# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Compliance sweep report model for aggregated handler compliance audits."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.governance.model_handler_compliance_result import (
    ModelHandlerComplianceResult,
)
from omnibase_core.models.governance.model_repo_compliance_breakdown import (
    ModelRepoComplianceBreakdown,
)


class ModelComplianceSweepReport(BaseModel):
    """Aggregated compliance sweep report across one or more repositories."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime = Field(..., description="When the sweep was performed")
    total_handlers: int = Field(..., description="Total handlers scanned", ge=0)
    compliant_count: int = Field(..., description="Compliant handler count", ge=0)
    imperative_count: int = Field(..., description="Imperative handler count", ge=0)
    hybrid_count: int = Field(..., description="Hybrid handler count", ge=0)
    allowlisted_count: int = Field(..., description="Allowlisted handler count", ge=0)
    missing_contract_count: int = Field(
        ..., description="Missing contract handler count", ge=0
    )
    compliant_pct: float = Field(
        ..., description="Percentage of compliant handlers (0-100)", ge=0.0, le=100.0
    )
    violation_histogram: dict[str, int] = Field(
        default_factory=dict,
        description="Count per EnumComplianceViolation value",
    )
    per_repo: dict[str, ModelRepoComplianceBreakdown] = Field(
        default_factory=dict,
        description="Breakdown by repository",
    )
    results: list[ModelHandlerComplianceResult] = Field(
        default_factory=list,
        description="Full audit details",
    )
    new_violations_since_last: list[str] = Field(
        default_factory=list,
        description="Handlers that gained violations since last sweep",
    )

    @model_validator(mode="after")
    def validate_aggregates(self) -> ModelComplianceSweepReport:
        categorized = (
            self.compliant_count
            + self.imperative_count
            + self.hybrid_count
            + self.allowlisted_count
            + self.missing_contract_count
        )
        if categorized != self.total_handlers:
            raise ValueError(
                f"total_handlers ({self.total_handlers}) must equal sum of all "
                f"verdict counts ({categorized})"
            )
        if self.total_handlers == 0:
            if self.compliant_pct != 0.0:
                raise ValueError("compliant_pct must be 0 when total_handlers is 0")
        else:
            expected_pct = (self.compliant_count / self.total_handlers) * 100.0
            if abs(self.compliant_pct - expected_pct) > 1e-6:
                raise ValueError(
                    f"compliant_pct ({self.compliant_pct}) must match "
                    f"compliant_count/total_handlers ({expected_pct:.6f})"
                )
        for key, count in self.violation_histogram.items():
            if count < 0:
                raise ValueError(
                    f"violation_histogram[{key!r}] must be non-negative, got {count}"
                )
        return self
