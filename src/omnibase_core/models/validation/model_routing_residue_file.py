# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Residue-file payload model for the routing-authority validator (OMN-13285)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelRoutingResidueFile(BaseModel):
    """A residue file under the env-authority burn-down ratchet.

    The validator FAILS only when the current violation count EXCEEDS
    ``baseline_count`` (a NEW violation introduced); a count at or below the
    baseline PASSES (grandfathered debt). ``kind`` selects the counting strategy:
    ``"python"`` (AST env-read scan) or ``"yaml_policy"`` (env_var field count).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repo-relative path of the residue file.")
    text: str = Field(description="Full UTF-8 text of the residue file.")
    kind: str = Field(
        description="'python' (AST env-read scan) or 'yaml_policy' (env_var field count)."
    )
    baseline_count: int = Field(
        ge=0, description="Maximum allowed violation count (pre-existing debt)."
    )
    debt_ticket: str = Field(description="Linear ticket owning the remediation debt.")
    description: str = Field(description="Human-readable description of the debt.")


__all__ = ["ModelRoutingResidueFile"]
