# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result of a finding detector."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.finding_baseline.model_source_finding import (
    ModelSourceFinding,
)

__all__ = ["ModelFindingDetectResult"]


class ModelFindingDetectResult(BaseModel):
    """Findings of one detector run, in file then line order."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    findings: tuple[ModelSourceFinding, ...] = Field(default=())
    files_checked: int = Field(default=0, ge=0)
