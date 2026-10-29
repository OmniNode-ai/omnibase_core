# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Result of the node-purity COMPUTE validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.node_purity_check.model_node_purity_check_finding import (
    ModelNodePurityCheckFinding,
)

__all__ = ["ModelNodePurityCheckOutput"]


class ModelNodePurityCheckOutput(BaseModel):
    """All node-purity violations found across the supplied source files."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    violations: tuple[ModelNodePurityCheckFinding, ...] = Field(default=())

    @property
    def is_clean(self) -> bool:
        """Return True iff no violations were found."""
        return not self.violations
