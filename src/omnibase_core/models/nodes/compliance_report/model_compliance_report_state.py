# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Aggregate compliance report state accumulated by the reducer."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.compliance_report.model_compliance_check_result import (
    ModelComplianceCheckResult,
)


class ModelComplianceReportState(BaseModel):
    """Aggregate compliance report state accumulated by the reducer."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    total: int = 0
    passed: int = 0
    failed: int = 0
    results: list[ModelComplianceCheckResult] = Field(default_factory=list)
    run_id: UUID | None = None
    repo_root: str | None = None
    scan_started_at: datetime | None = None
