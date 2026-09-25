# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""An event a component must reject in a state (OMN-19553)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelContractWalkIllegalPair(BaseModel):
    """A (state, trigger) pair with no declared transition.

    The trigger belongs to the component's declared alphabet and the state is
    reached in the walk and is not terminal, so an arriving event of this kind
    is invalid in that state and must be rejected, not silently accepted."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node: str = Field(description="Node whose machine owns the state")
    state: str = Field(description="Reached, non-terminal state")
    trigger: str = Field(
        description="Declared trigger with no transition out of the state"
    )
