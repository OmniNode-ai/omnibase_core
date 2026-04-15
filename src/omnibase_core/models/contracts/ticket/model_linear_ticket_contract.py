# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelTicketContract — Pydantic v2 schema for Linear ticket contracts.

Validates that every ticket cited in a PR has a complete, non-empty contract
with dod_evidence, golden_path, and deploy_step when the ticket touches runtime.

OMN-8916
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.models.contracts.ticket.model_dod_evidence_item import (
    ModelDodEvidenceItem,
)

_TICKET_ID_RE = re.compile(r"^OMN-\d+$")


class ModelTicketContract(BaseModel):
    """Canonical contract for a Linear ticket cited in a PR.

    Enforces that dod_evidence and golden_path are non-empty, and that
    runtime-touching tickets declare a deploy_step.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticket_id: str = Field(..., description="Linear ticket ID matching OMN-\\d+")
    title: str = Field(..., min_length=1)
    dod_evidence: list[ModelDodEvidenceItem] = Field(..., min_length=1)
    golden_path: str = Field(..., min_length=1)
    runtime_change: bool = Field(default=False)
    deploy_step: str | None = Field(default=None)

    @field_validator("ticket_id")
    @classmethod
    def validate_ticket_id(cls, v: str) -> str:
        if not _TICKET_ID_RE.match(v):
            raise ValueError(f"ticket_id must match OMN-\\d+, got: {v!r}")
        return v

    @model_validator(mode="after")
    def validate_deploy_step_when_runtime_change(self) -> ModelTicketContract:
        if self.runtime_change and not self.deploy_step:
            raise ValueError("deploy_step is required when runtime_change=True")
        return self


__all__ = ["ModelTicketContract"]
