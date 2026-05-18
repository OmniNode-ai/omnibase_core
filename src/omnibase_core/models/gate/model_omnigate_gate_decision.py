# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OmniGate gate decision model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_omnigate import EnumGateEnforcementAction


class ModelOmniGateGateDecision(BaseModel):
    """Verification decision written for dumb GitHub API application."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: EnumGateEnforcementAction
    reason: str
    label: str | None = None
    comment_body: str | None = None


__all__ = ["ModelOmniGateGateDecision"]
