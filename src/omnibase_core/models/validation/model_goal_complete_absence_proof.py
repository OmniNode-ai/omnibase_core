# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalCompleteAbsenceProof."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from omnibase_core.constants.constants_goal_admission import (
    _REPOSITORY_RE,
    _SHA256_RE,
)


class ModelGoalCompleteAbsenceProof(BaseModel):
    """Authenticated complete App scan proving no check exists for one head."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    app_integration_id: str = Field(  # string-id-ok: GitHub App installation identifier
        ..., min_length=1, max_length=128
    )
    repository: str
    goal_id: UUID
    context_name: str = Field(..., min_length=1, max_length=256)
    head_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    query_sha256: str
    page_count: int = Field(..., ge=1, le=1000)
    records_read: int = Field(..., ge=0)
    total_count: int = Field(..., ge=0)
    terminal_cursor_sha256: str
    page_chain_sha256: str
    captured_at: datetime
    complete: Literal[True]

    @field_validator("query_sha256", "terminal_cursor_sha256", "page_chain_sha256")
    @classmethod
    def _scan_digests_are_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("scan digests must use sha256:<64 lowercase hex>")
        return value

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @model_validator(mode="after")
    def _scan_is_complete_empty(self) -> Self:
        if self.records_read != 0 or self.total_count != 0:
            raise ValueError("complete-absence scan must contain zero runs")
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must include a timezone")
        return self
