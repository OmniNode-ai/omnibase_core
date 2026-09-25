# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A declared state of one component contract (OMN-19553)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelContractWalkStateRef(BaseModel):
    """Names one declared state of one component."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node: str = Field(description="Node whose machine declares the state")
    state: str = Field(description="Declared state name")
