# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic result of the venv build-lock check (OMN-22649)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue


class ModelVenvBuildLockCheckResult(BaseModel):
    """Issues and the count of surfaces judged."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    issues: tuple[ModelValidationIssue, ...] = Field(
        description="Enabled rule violations and the stated non-evaluations"
    )
    surfaces_judged: int = Field(description="Surfaces compared with their build lock")
