# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Rollup-coverage gaps found by the Model-B verifier."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_rollup_coverage_gap import (
    ModelRollupCoverageGap,
)


class ModelRollupCoverageCheckOutput(BaseModel):
    """Whether the repo is opted into Model B, and the gaps found when it is."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    opted_in: bool
    gaps: tuple[ModelRollupCoverageGap, ...] = ()
