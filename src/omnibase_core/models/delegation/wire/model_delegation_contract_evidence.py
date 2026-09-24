# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Observed response-contract delivery evidence."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_delegation_output_shape import EnumDelegationOutputShape
from omnibase_core.models.delegation.wire.model_delegation_raw_response import (
    ModelDelegationRawResponse,
)


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
    raw_response: ModelDelegationRawResponse | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "The provider's response content exactly as returned, before any "
            "extraction (OMN-19385). The output-only release bar judges the "
            "caller's bytes against it. Absent when the producer predates the "
            "carrier or the attempt produced no response."
        ),
    )

    @field_validator("contract_sha256")
    @classmethod
    def _validate_contract_sha256(cls, value: str) -> str:
        if any(character not in "0123456789abcdef" for character in value):
            raise ValueError("contract_sha256 must be lowercase hexadecimal")
        return value


__all__ = ["ModelDelegationContractEvidence"]
