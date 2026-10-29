# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Result of the lane-literal branching COMPUTE validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_lane_literal_branching_violation import (
    ModelLaneLiteralBranchingViolation,
)

__all__ = ["ModelNoLaneLiteralBranchingCheckOutput"]


class ModelNoLaneLiteralBranchingCheckOutput(BaseModel):
    """All lane-literal branching findings across the supplied source files."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    violations: tuple[ModelLaneLiteralBranchingViolation, ...] = Field(default=())

    @property
    def is_clean(self) -> bool:
        """Return True iff no findings were produced."""
        return not self.violations
