# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protected database proof that a goal-owned publication scope is empty."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.constants.constants_goal_admission import _REPOSITORY_RE


class ModelGoalMutationScopeAbsenceProof(BaseModel):
    """Exact fenced proof that a goal has no App contexts or attempt subjects.

    This proof describes the canonical App-owned goal scope, not every PR in a
    repository. Its producer must read the App publication journal and attempt
    store under their shared repository/goal lock and provide the resulting
    scope revisions. The model validates shape; the protected store establishes
    authority by rereading and matching these rows and fences.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: str
    goal_id: UUID
    intent_id: UUID
    app_integration_id: str = Field(  # string-id-ok: GitHub App installation identifier
        ..., min_length=1, max_length=128
    )
    required_context_name: str = Field(..., min_length=1, max_length=256)
    publication_store_revision: UUID
    attempt_store_revision: UUID
    attempt_subject_count: Literal[0]
    journal_context_count: Literal[0]
    unresolved_publication_intent_count: Literal[0]
    captured_at: datetime

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @model_validator(mode="after")
    def _scope_proof_is_bound(self) -> Self:
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must include a timezone")
        return self
