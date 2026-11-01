# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed contract-chain facts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.validation.model_contract_chain_binding import (
    ModelContractChainBinding,
)


class ModelContractChainFacts(BaseModel):
    """Strictly parsed corpus documents, armed machines and binding evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    documents: dict[str, dict[str, JsonValue]] = Field(default_factory=dict)
    fsms: dict[str, ModelFSMSubcontract] = Field(default_factory=dict)
    bindings: tuple[ModelContractChainBinding, ...] = ()
