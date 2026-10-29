# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the pure design-record check (OMN-21509)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)


class ModelDesignRecordCheckInput(BaseModel):
    """The record text and the contract that defines its rules."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    text: str = Field(description="Plan or ticket body containing the design record")
    contract: ModelValidatorSubcontract = Field(
        description="Design-record validation rules"
    )
