# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A declared transition of one component contract (OMN-19553)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelContractWalkTransitionRef(BaseModel):
    """Names one declared transition of one component by node and endpoints."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node: str = Field(
        description="Node (contract directory) that declares the transition"
    )
    transition_name: str = Field(description="Declared transition name")
    from_state: str = Field(description="Declared source state, or * for a wildcard")
    trigger: str = Field(description="Declared trigger")
    to_state: str = Field(description="Declared target state")
