# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A machine-declaring contract the walker cannot walk (OMN-19553)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelContractWalkNotArmed(BaseModel):
    """A contract that declares a machine the walker cannot load strictly.

    NOT_ARMED contracts stay in every report and in the denominator; they are
    never dropped (plan r4 Phase -1, NOT_ARMED not absent)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node: str = Field(description="Node (contract directory name)")
    contract_path: str = Field(description="Contract path relative to the scanned root")
    reason: str = Field(description="The specific missing or unknown declaration")
