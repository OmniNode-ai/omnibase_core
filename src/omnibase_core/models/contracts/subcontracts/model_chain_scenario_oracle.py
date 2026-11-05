# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Oracle statement of a chain scenario case (OMN-22478)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_chain_scenario_oracle_basis import (
    EnumChainScenarioOracleBasis,
)


class ModelChainScenarioOracle(BaseModel):
    """Why the expected result is right, stated by someone other than the handler."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    basis: EnumChainScenarioOracleBasis
    statement: str = Field(
        ..., min_length=1, description="The rule the expectations follow from."
    )


__all__ = ["ModelChainScenarioOracle"]
