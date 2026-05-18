# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDoctrineClause — deterministic truth doctrine clause model — OMN-11193."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDoctrineClause"]


class ModelDoctrineClause(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-id-ok: domain-specific human-readable code (DT-NNN), not an internal UUID
    clause_id: str = Field(..., pattern=r"^DT-\d{3}$")
    title: str = Field(..., min_length=1)
    check: str = Field(..., min_length=1)
    ci_gate: str = Field(..., min_length=1)
    adr: str | None = None
    coverage: str = Field(default="uncovered")
