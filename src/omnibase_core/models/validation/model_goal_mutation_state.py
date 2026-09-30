# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalMutationState."""

from __future__ import annotations

import hashlib
import json
from typing import Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
    model_validator,
)

from omnibase_core.constants.constants_goal_admission import (
    _REPOSITORY_RE,
)
from omnibase_core.models.validation.model_goal_mutation_confirmation import (
    ModelGoalMutationConfirmation,
)
from omnibase_core.models.validation.model_goal_mutation_intent import (
    ModelGoalMutationIntent,
)


class ModelGoalMutationState(BaseModel):
    """Protected current mutation barrier state for one goal partition."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: str
    goal_id: UUID
    store_revision: UUID
    status: Literal["clear", "pending", "sending", "uncertain", "blocked_confirmed"]
    intent: ModelGoalMutationIntent | None = None
    confirmation: ModelGoalMutationConfirmation | None = None

    @model_validator(mode="after")
    def _barrier_state_is_consistent(self) -> Self:
        if (self.status == "clear") != (self.intent is None):
            raise ValueError(
                "clear mutation state has no intent; blocked states require one"
            )
        if self.intent is not None and (
            self.intent.repository != self.repository
            or self.intent.goal_id != self.goal_id
        ):
            raise ValueError("mutation intent is outside the protected scope")
        if self.status == "blocked_confirmed":
            if self.confirmation is None or self.intent is None:
                raise ValueError(
                    "confirmed barrier requires its intent and confirmation"
                )
            if (
                self.confirmation.intent_id != self.intent.intent_id
                or self.confirmation.intent_sha256 != self.intent.content_sha256()
            ):
                raise ValueError("confirmation does not match the current intent")
        elif self.confirmation is not None:
            raise ValueError("only a confirmed barrier may carry a confirmation")
        return self

    def content_sha256(self) -> str:
        payload = self.model_dump(mode="json")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @model_validator(mode="after")
    def _state_confirmation_is_scoped(self) -> Self:
        if self.confirmation is not None and (
            self.confirmation.repository != self.repository
            or self.confirmation.goal_id != self.goal_id
        ):
            raise ValueError("mutation confirmation is outside the protected scope")
        return self
