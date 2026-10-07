# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Result of the pure node-home ratchet (OMN-20702)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_node_home_ratchet_finding import (
    ModelNodeHomeRatchetFinding,
)


class ModelNodeHomeRatchetResult(BaseModel):
    """All sorted node directories and any violations of the ratchet."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_directories: tuple[str, ...]
    findings: tuple[ModelNodeHomeRatchetFinding, ...]


__all__ = ["ModelNodeHomeRatchetResult"]
