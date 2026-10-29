# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result of shrinking a baseline against a run's findings."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.finding_baseline.model_finding_baseline_entry import (
    ModelFindingBaselineEntry,
)
from omnibase_core.models.finding_baseline.model_source_finding import (
    ModelSourceFinding,
)

__all__ = ["ModelFindingBaselineShrink"]


class ModelFindingBaselineShrink(BaseModel):
    """The entries that survive, and the findings no entry covers (a write is refused)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kept: tuple[ModelFindingBaselineEntry, ...] = Field(default=())
    added: tuple[ModelSourceFinding, ...] = Field(default=())
    unbaselinable: tuple[ModelSourceFinding, ...] = Field(default=())
