# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A strictly loaded contract machine the walker composes (OMN-19553)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_contract_walk import EnumContractWalkRole
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)


class ModelContractWalkMachine(BaseModel):
    """One machine-declaring contract that passed the strict load.

    Carries what linking needs besides the machine: the declared event_bus
    topics and every string value in the contract (module paths among them).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node: str = Field(description="Node (contract directory name)")
    contract_path: str = Field(description="Contract path relative to the scanned root")
    role: EnumContractWalkRole = Field(description="Role from the contract's node_type")
    fsm: ModelFSMSubcontract = Field(description="The strictly loaded state machine")
    publishes: frozenset[str] = Field(description="Declared event_bus publish topics")
    subscribes: frozenset[str] = Field(
        description="Declared event_bus subscribe topics"
    )
    strings: tuple[str, ...] = Field(description="Every string value in the contract")
