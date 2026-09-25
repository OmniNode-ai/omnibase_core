# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One contract machine inside a walked workflow (OMN-19553)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_contract_walk import (
    EnumContractWalkLinkEvidence,
    EnumContractWalkRole,
)


class ModelContractWalkComponent(BaseModel):
    """A machine-declaring contract taking part in a workflow."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node: str = Field(description="Node (contract directory name)")
    contract_path: str = Field(description="Contract path relative to the scanned root")
    role: EnumContractWalkRole = Field(description="Role in the workflow")
    link_evidence: tuple[EnumContractWalkLinkEvidence, ...] = Field(
        default=(),
        description="How the contracts declare the link to the workflow owner",
    )
    link_detail: tuple[str, ...] = Field(
        default=(), description="The declared topics or module references that link it"
    )
    state_count: int = Field(description="Declared states")
    transition_count: int = Field(description="Declared transitions")
    perpetual: bool = Field(
        description="True when the machine declares no terminal state"
    )
    analyze_fsm_errors: tuple[str, ...] = Field(
        default=(), description="analyze_fsm findings for this machine on its own"
    )
