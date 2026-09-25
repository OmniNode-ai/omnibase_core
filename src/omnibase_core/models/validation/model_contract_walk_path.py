# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A selected path through a workflow's product graph (OMN-19553)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_contract_walk import EnumContractWalkPathKind
from omnibase_core.models.validation.model_contract_walk_step import (
    ModelContractWalkStep,
)


class ModelContractWalkPath(BaseModel):
    """A path from the initial product state, selected by the all-edges cover."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: EnumContractWalkPathKind = Field(description="How the path ends")
    steps: tuple[ModelContractWalkStep, ...] = Field(
        description="Edges in firing order"
    )
    end_state: tuple[str, ...] = Field(description="Product state the path ends in")
