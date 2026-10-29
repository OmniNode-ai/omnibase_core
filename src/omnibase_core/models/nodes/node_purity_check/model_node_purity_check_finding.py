# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One node-purity violation reported by the node-purity COMPUTE validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelNodePurityCheckFinding"]


class ModelNodePurityCheckFinding(BaseModel):
    """A single node-purity violation, with the rule as its string value."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    file: str
    line: int
    column: int
    rule: str
    message: str
