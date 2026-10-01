# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structured operator selection resolving one append-only goal revision fork."""

from __future__ import annotations

import re
import uuid

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

__all__ = ["ModelWorkGoalRevisionResolution"]

_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")


class ModelWorkGoalRevisionResolution(BaseModel):
    """Name every competing child revision and the selected head explicitly."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    goal_id: uuid.UUID
    repository: str
    fork_parent_revision_id: uuid.UUID
    competing_revision_ids: tuple[uuid.UUID, ...] = Field(..., min_length=2)
    selected_revision_id: uuid.UUID
    resolution_policy_revision: uuid.UUID

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @model_validator(mode="after")
    def _selection_is_unique_competitor(self) -> ModelWorkGoalRevisionResolution:
        if len(set(self.competing_revision_ids)) != len(self.competing_revision_ids):
            raise ValueError("a fork resolution must name each competing head once")
        if self.selected_revision_id not in self.competing_revision_ids:
            raise ValueError("selected_revision_id must be one of the competing heads")
        if self.fork_parent_revision_id in self.competing_revision_ids:
            raise ValueError("a fork parent cannot be one of its child heads")
        return self

    @field_serializer("competing_revision_ids")
    def _serialize_competing_ids_sorted(
        self, value: tuple[uuid.UUID, ...]
    ) -> list[str]:
        return sorted(str(revision_id) for revision_id in value)
