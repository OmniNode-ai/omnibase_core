# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A validator subcontract file with its standard ``validation:`` envelope."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)

__all__ = ["ModelValidatorContractFile"]


class ModelValidatorContractFile(BaseModel):
    """The shape of a ``*.validation.yaml`` file."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contract_kind: str = Field(
        default="validation_subcontract", description="Always validation_subcontract"
    )
    validation: ModelValidatorSubcontract = Field(description="The subcontract")
