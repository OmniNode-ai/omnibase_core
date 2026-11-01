# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed contract-chain coverage row."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_contract_chain_obligation_kind import (
    EnumContractChainObligationKind,
)


class ModelContractChainCoverageRow(BaseModel):
    """One obligation with its first binding and all declared overlays."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    owner: str
    kind: EnumContractChainObligationKind
    id: str
    location: str
    overlays: tuple[str, ...] = ()
