# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result of comparing a run's findings with a baseline."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.finding_baseline.model_finding_baseline_entry import (
    ModelFindingBaselineEntry,
)
from omnibase_core.models.finding_baseline.model_source_finding import (
    ModelSourceFinding,
)

__all__ = ["ModelFindingBaselineComparison"]


class ModelFindingBaselineComparison(BaseModel):
    """What fails: findings outside the baseline, entries with no finding, hard errors."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    new: tuple[ModelSourceFinding, ...] = Field(default=())
    stale: tuple[ModelFindingBaselineEntry, ...] = Field(default=())
    unbaselinable: tuple[ModelSourceFinding, ...] = Field(default=())
