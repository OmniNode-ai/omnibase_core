# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed contract-chain obligation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_contract_chain_obligation_kind import (
    EnumContractChainObligationKind,
)


class ModelContractChainObligation(BaseModel):
    """An obligation derived from an armed FSM or execution graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    owner: str
    kind: EnumContractChainObligationKind
    id: str
