# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-node compliance check result."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.compliance_report.model_compliance_check_detail import (
    ModelComplianceCheckDetail,
)


class ModelComplianceCheckResult(BaseModel):
    """Result of compliance checks for a single node."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node_id: str
    passed: bool
    checks: tuple[ModelComplianceCheckDetail, ...] = Field(default_factory=tuple)
