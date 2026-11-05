# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Mutation receipt of one case under one named break (OMN-22478)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_chain_scenario_break import EnumChainScenarioBreak


class ModelChainScenarioReceipt(BaseModel):
    """The kept evidence that a case went red (or stayed green) under a break."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_name: str = Field(..., min_length=1)
    case_hash: str = Field(
        ..., min_length=1, description="Hash of the case the run used."
    )
    injected_break: EnumChainScenarioBreak
    outcome: Literal["red", "green"]
    failed_assertion: str = Field(
        default="",
        description="The assertion that fired; empty when the case stayed green.",
    )


__all__ = ["ModelChainScenarioReceipt"]
