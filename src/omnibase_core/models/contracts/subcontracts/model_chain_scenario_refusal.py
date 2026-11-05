# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Refusal that says why a node cannot carry a chain scenario yet (OMN-22478)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_chain_scenario_kind import EnumChainScenarioKind
from omnibase_core.enums.enum_chain_scenario_refusal_kind import (
    EnumChainScenarioRefusalKind,
)


class ModelChainScenarioRefusal(BaseModel):
    """A declared refusal: what it covers, the reason and the ticket that lifts it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    applies_to: EnumChainScenarioKind
    subject: str = Field(
        ...,
        min_length=1,
        description="Success topic (golden) or failure name (error) it covers.",
    )
    kind: EnumChainScenarioRefusalKind
    reason: str = Field(
        ..., min_length=1, description="Why no case can be written today."
    )
    unblocked_by: str = Field(
        ..., min_length=1, description="Ticket whose change lifts the refusal."
    )


__all__ = ["ModelChainScenarioRefusal"]
