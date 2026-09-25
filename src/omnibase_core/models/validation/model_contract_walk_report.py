# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Machine-readable report of one contract walk (OMN-19553)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_contract_walk_not_armed import (
    ModelContractWalkNotArmed,
)
from omnibase_core.models.validation.model_contract_walk_summary import (
    ModelContractWalkSummary,
)
from omnibase_core.models.validation.model_contract_walk_workflow import (
    ModelContractWalkWorkflow,
)


class ModelContractWalkReport(BaseModel):
    """The walker's full, deterministic report. Report-only: nothing in it fails a build."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    report_kind: str = Field(
        default="contract_walk.v1", description="Report schema identifier"
    )
    roots: tuple[str, ...] = Field(description="Scanned roots, as given")
    summary: ModelContractWalkSummary = Field(description="Totals")
    not_armed: tuple[ModelContractWalkNotArmed, ...] = Field(
        default=(), description="Machine contracts the walker could not load strictly"
    )
    workflows: tuple[ModelContractWalkWorkflow, ...] = Field(
        default=(), description="One entry per walked workflow"
    )
