# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Request of the shared baseline handler."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.finding_baseline.model_finding_baseline import (
    ModelFindingBaseline,
)
from omnibase_core.models.finding_baseline.model_finding_baseline_scope import (
    ModelFindingBaselineScope,
)
from omnibase_core.models.finding_baseline.model_source_finding import (
    ModelSourceFinding,
)

__all__ = ["ModelFindingBaselineInput"]


class ModelFindingBaselineInput(BaseModel):
    """Findings of a run, the hook's baseline (None means no ``--baseline``), the scope."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    hook_id: str = Field(min_length=1)
    findings: tuple[ModelSourceFinding, ...] = Field(default=())
    baseline: ModelFindingBaseline | None = None
    scope: ModelFindingBaselineScope = Field(default_factory=ModelFindingBaselineScope)
    remediation: str | None = None
