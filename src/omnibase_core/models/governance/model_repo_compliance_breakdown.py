# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-repo compliance breakdown model for compliance sweep reports."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelRepoComplianceBreakdown(BaseModel):
    """Per-repo breakdown of compliance results."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: str = Field(..., description="Repository name")
    total_handlers: int = Field(..., description="Total handlers scanned", ge=0)
    compliant: int = Field(..., description="Compliant handler count", ge=0)
    imperative: int = Field(..., description="Imperative handler count", ge=0)
    hybrid: int = Field(..., description="Hybrid handler count", ge=0)
    top_violations: list[str] = Field(
        default_factory=list,
        description="Most common violation types in this repo",
    )
