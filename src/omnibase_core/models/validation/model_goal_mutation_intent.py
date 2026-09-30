# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalMutationIntent."""

from __future__ import annotations

import hashlib
import json
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
    _GIT_SHA_RE,
    _REPOSITORY_RE,
    _SHA256_RE,
)
from omnibase_core.models.validation.model_goal_mutation_context import (
    ModelGoalMutationContext,
)
from omnibase_core.models.validation.model_goal_mutation_revision import (
    ModelGoalMutationRevision,
)


class ModelGoalMutationIntent(BaseModel):
    """Durable barrier intent before changing goal or policy authority."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent_id: UUID
    nonce: UUID
    repository: str
    goal_id: UUID
    mutation_kind: Literal["contract_revision", "policy_revision", "deadline_expiry"]
    app_integration_id: str = Field(  # string-id-ok: GitHub App installation identifier
        ..., min_length=1, max_length=128
    )
    required_context_name: str = Field(..., min_length=1, max_length=256)
    current_contract_revision: UUID | None = None
    current_contract_sha256: str | None = None
    current_contract_revisions: tuple[ModelGoalMutationRevision, ...] = Field(
        default_factory=tuple
    )
    proposed_contract_revision: UUID
    proposed_contract_sha256: str
    current_policy_revision: UUID | None = None
    current_policy_sha256: str | None = None
    proposed_policy_revision: UUID
    proposed_policy_sha256: str
    history_store_revision: UUID
    policy_store_revision: UUID
    observation_store_revision: UUID
    attempt_store_revision: UUID
    publication_store_revision: UUID
    affected_contexts: tuple[ModelGoalMutationContext, ...] = Field(
        default_factory=tuple
    )
    affected_head_shas: tuple[str, ...]
    created_at: datetime

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @field_validator(
        "current_contract_sha256",
        "proposed_contract_sha256",
        "current_policy_sha256",
        "proposed_policy_sha256",
    )
    @classmethod
    def _optional_digest_is_canonical(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256_RE.fullmatch(value):
            raise ValueError("mutation digests must use sha256:<64 lowercase hex>")
        return value

    @field_validator("affected_head_shas")
    @classmethod
    def _heads_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not _GIT_SHA_RE.fullmatch(value) for value in values):
            raise ValueError("affected heads must be full lowercase Git object IDs")
        if len(set(values)) != len(values):
            raise ValueError("affected heads must be unique")
        return tuple(sorted(values))

    @model_validator(mode="after")
    def _intent_is_bound(self) -> Self:
        if (self.current_contract_revision is None) != (
            self.current_contract_sha256 is None
        ):
            raise ValueError("current contract revision and digest must be paired")
        current_revision_ids = {
            revision.revision_id for revision in self.current_contract_revisions
        }
        if self.current_contract_revisions:
            if self.current_contract_revision is not None:
                raise ValueError(
                    "singular and competing current contract revisions cannot mix"
                )
            if len(self.current_contract_revisions) < 2:
                raise ValueError(
                    "competing current contract revisions must contain a fork"
                )
            if len(current_revision_ids) != len(self.current_contract_revisions):
                raise ValueError("current contract revisions must be unique")
        if (self.current_policy_revision is None) != (
            self.current_policy_sha256 is None
        ):
            raise ValueError("current policy revision and digest must be paired")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        if len(set(self.affected_contexts)) != len(self.affected_contexts):
            raise ValueError("affected App contexts must be unique")
        if not self.affected_head_shas and self.affected_contexts:
            raise ValueError("empty affected-head set cannot contain App contexts")
        for context in self.affected_contexts:
            context_revision_is_current = (
                context.contract_revision in current_revision_ids
                if self.current_contract_revisions
                else context.contract_revision == self.current_contract_revision
            )
            if (
                context.app_integration_id != self.app_integration_id
                or context.context_name != self.required_context_name
                or context.head_sha not in self.affected_head_shas
                or not context_revision_is_current
            ):
                raise ValueError("affected context does not match mutation scope")
        return self

    def content_sha256(self) -> str:
        payload = self.model_dump(mode="json")
        payload["affected_contexts"] = sorted(
            payload["affected_contexts"],
            key=lambda context: (
                context["head_sha"],
                context["context_name"],
                context["check_run_id"],
            ),
        )
        payload["affected_head_shas"] = sorted(self.affected_head_shas)
        payload["current_contract_revisions"] = sorted(
            payload["current_contract_revisions"],
            key=lambda revision: revision["revision_id"],
        )
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
