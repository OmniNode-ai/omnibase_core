# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Observed response-contract delivery evidence."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_delegation_output_shape import EnumDelegationOutputShape


class ModelDelegationContractEvidence(BaseModel):
    """Evidence stamped only after the provider-boundary request is formed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    conveyed: bool = Field(
        description="Whether the outbound provider request carried the contract."
    )
    validated: bool = Field(
        description="Whether the quality gate validated the extracted deliverable."
    )
    output_shape: EnumDelegationOutputShape = Field(
        description="Declared shape used by extraction and validation."
    )
    contract_sha256: str = Field(min_length=64, max_length=64)
    channel: str = Field(min_length=1)

    @field_validator("contract_sha256")
    @classmethod
    def _validate_contract_sha256(cls, value: str) -> str:
        if any(character not in "0123456789abcdef" for character in value):
            raise ValueError("contract_sha256 must be lowercase hexadecimal")
        return value


__all__ = ["ModelDelegationContractEvidence"]
