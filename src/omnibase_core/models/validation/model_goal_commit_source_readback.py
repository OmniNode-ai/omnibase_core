# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Authenticated current source readback for a goal commit subject."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.constants.constants_goal_admission import (
    _REPOSITORY_RE,
    is_canonical_git_head_ref,
)


class ModelGoalCommitSourceReadback(BaseModel):
    """Current authenticated PR-head or branch-head identity from Market."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: str
    goal_id: UUID
    contract_revision: UUID
    commit_source: Literal["pull_request", "branch"]
    subject_ref: str
    subject_repository: str
    subject_commit_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    subject_tree_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    pull_request_number: int | None = Field(default=None, ge=1)
    base_repository: str | None = None
    base_ref: str | None = None
    observed_at: datetime

    @field_validator("repository", "subject_repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @model_validator(mode="after")
    def _source_identity_is_complete(self) -> ModelGoalCommitSourceReadback:
        if not is_canonical_git_head_ref(self.subject_ref):
            raise ValueError("subject_ref must be a fully qualified Git head ref")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        if self.commit_source == "pull_request":
            if (
                self.pull_request_number is None
                or self.base_repository != self.repository
                or self.base_ref is None
                or not is_canonical_git_head_ref(self.base_ref)
            ):
                raise ValueError(
                    "pull-request readback requires exact PR and base repository/ref"
                )
        elif (
            self.subject_repository != self.repository
            or self.pull_request_number is not None
            or self.base_repository is not None
            or self.base_ref is not None
        ):
            raise ValueError(
                "branch readback must use the goal repository without PR metadata"
            )
        return self


__all__ = ["ModelGoalCommitSourceReadback"]
