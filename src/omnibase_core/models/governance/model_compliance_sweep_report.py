# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Compliance sweep report model for aggregated handler compliance audits."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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
