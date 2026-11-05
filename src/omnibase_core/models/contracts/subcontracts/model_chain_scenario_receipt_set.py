# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Mutation receipts kept next to a node contract (OMN-22478)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_chain_scenario_receipt import (
    ModelChainScenarioReceipt,
)


class ModelChainScenarioReceiptSet(BaseModel):
    """All receipts of one node, as the generated test writes and re-proves them."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = Field(..., ge=1)
    node: str = Field(..., min_length=1)
    receipts: tuple[ModelChainScenarioReceipt, ...] = ()


__all__ = ["ModelChainScenarioReceiptSet"]
