# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalRevisionAuthorizationPolicy."""

from __future__ import annotations

import hashlib
import json
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


class ModelGoalRevisionAuthorizationPolicy(BaseModel):
    """Immutable trusted policy naming actors allowed to resolve goal forks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: str
    goal_id: UUID
    policy_revision: UUID
    allowed_actor_keys: tuple[str, ...] = Field(..., min_length=1)
    allowed_event_runtime_ids: tuple[str, ...] = Field(..., min_length=1)
    policy_sha256: str

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @field_validator("allowed_actor_keys", "allowed_event_runtime_ids")
    @classmethod
    def _authorized_identities_are_unique_nonblank(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        if any(not value.strip() for value in values) or len(set(values)) != len(
            values
        ):
            raise ValueError("allowed actor keys must be unique and nonblank")
        return values

    @field_validator("policy_sha256")
    @classmethod
    def _policy_digest_is_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("policy digest must use sha256:<64 lowercase hex>")
        return value

    def content_sha256(self) -> str:
        payload = {
            "repository": self.repository,
            "goal_id": str(self.goal_id),
            "policy_revision": str(self.policy_revision),
            "allowed_actor_keys": sorted(self.allowed_actor_keys),
            "allowed_event_runtime_ids": sorted(self.allowed_event_runtime_ids),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"

    @model_validator(mode="after")
    def _digest_matches_policy(self) -> ModelGoalRevisionAuthorizationPolicy:
        if self.content_sha256() != self.policy_sha256:
            raise ValueError("revision authorization policy digest mismatch")
        return self
