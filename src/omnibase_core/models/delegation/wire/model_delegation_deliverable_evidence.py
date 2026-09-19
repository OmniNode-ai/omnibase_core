# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Exact extraction evidence carried from a response boundary to the quality gate."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_delegation_output_shape import EnumDelegationOutputShape


class ModelDelegationDeliverableEvidence(BaseModel):
    """Declared-contract span evidence for one cleaned customer deliverable."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    output_shape: EnumDelegationOutputShape
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deliverable_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deliverable_chars: int = Field(ge=0)
    preamble_chars: int = Field(ge=0)
    raw_chars: int = Field(ge=0)
    deliverable_start: int = Field(ge=0)
    deliverable_end: int = Field(ge=0)

    @model_validator(mode="after")
    def _validate_span(self) -> ModelDelegationDeliverableEvidence:
        if self.deliverable_start != self.preamble_chars:
            raise ValueError("deliverable_start must equal preamble_chars")
        if self.deliverable_end < self.deliverable_start:
            raise ValueError("deliverable_end must not precede deliverable_start")
        if self.deliverable_end > self.raw_chars:
            raise ValueError("deliverable_end must not exceed raw_chars")
        return self


__all__ = ["ModelDelegationDeliverableEvidence"]
