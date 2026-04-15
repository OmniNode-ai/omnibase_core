# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDodEvidenceItem — a single DoD evidence entry for a Linear ticket. OMN-8916"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.ticket.model_dod_evidence_check import (
    ModelDodEvidenceCheck,
)


class ModelDodEvidenceItem(BaseModel):
    """A single DoD evidence entry declaring what must be verified before Done."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    checks: list[ModelDodEvidenceCheck] = Field(default_factory=list)


__all__ = ["ModelDodEvidenceItem"]
