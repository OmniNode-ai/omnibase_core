# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalMutationConfirmation."""

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
    _REPOSITORY_RE,
    _SHA256_RE,
)
from omnibase_core.models.validation.model_goal_complete_absence_proof import (
    ModelGoalCompleteAbsenceProof,
)
from omnibase_core.models.validation.model_goal_mutation_context import (
    ModelGoalMutationContext,
)
from omnibase_core.models.validation.model_goal_mutation_context_readback import (
    ModelGoalMutationContextReadback,
)
from omnibase_core.models.validation.model_goal_mutation_intent import (
    ModelGoalMutationIntent,
)
from omnibase_core.models.validation.model_goal_mutation_scope_absence_proof import (
    ModelGoalMutationScopeAbsenceProof,
)


class ModelGoalMutationConfirmation(BaseModel):
    """Durable confirmation that all prior checks are blocked or absent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent_id: UUID
    intent_sha256: str
    intent: ModelGoalMutationIntent
    repository: str
    goal_id: UUID
    outcome: Literal["all_blocked", "complete_absence", "mixed"]
    issued_contexts: tuple[ModelGoalMutationContext, ...] = Field(default_factory=tuple)
    readbacks: tuple[ModelGoalMutationContextReadback, ...] = Field(
        default_factory=tuple
    )
    absence_proofs: tuple[ModelGoalCompleteAbsenceProof, ...] = Field(
        default_factory=tuple
    )
    scope_absence_proof: ModelGoalMutationScopeAbsenceProof | None = None
    confirmed_at: datetime
    confirmation_sha256: str

    @field_validator("intent_sha256", "confirmation_sha256")
    @classmethod
    def _confirmation_digests_are_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("confirmation digests must use sha256:<64 lowercase hex>")
        return value

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @model_validator(mode="after")
    def _confirmation_shape_is_exact(self) -> Self:
        if self.confirmed_at.tzinfo is None or self.confirmed_at.utcoffset() is None:
            raise ValueError("confirmed_at must include a timezone")
        if self.outcome == "all_blocked" and not self.issued_contexts:
            raise ValueError("all_blocked requires the protected issued contexts")
        if self.outcome == "complete_absence" and self.issued_contexts:
            raise ValueError("complete_absence requires no issued contexts")
        if self.outcome == "mixed" and (
            not self.issued_contexts or not self.absence_proofs
        ):
            raise ValueError("mixed confirmation requires contexts and absence proofs")
        if not self.intent.affected_head_shas:
            if (
                self.outcome != "complete_absence"
                or self.scope_absence_proof is None
                or self.absence_proofs
            ):
                raise ValueError(
                    "empty goal scope requires one protected scope-absence proof"
                )
        elif self.scope_absence_proof is not None:
            raise ValueError(
                "scope-absence proof is only valid when no owned heads exist"
            )
        if any(readback.intent_id != self.intent_id for readback in self.readbacks):
            raise ValueError("App readback refers to a different mutation intent")
        if (
            self.intent.intent_id != self.intent_id
            or self.intent.content_sha256() != self.intent_sha256
            or self.intent.repository != self.repository
            or self.intent.goal_id != self.goal_id
        ):
            raise ValueError("confirmation intent binding is invalid")
        if self.issued_contexts != self.intent.affected_contexts:
            raise ValueError("issued contexts differ from the protected intent")
        expected = {
            (context.head_sha, context.context_name, context.check_run_id): context
            for context in self.issued_contexts
        }
        actual = {
            (item.head_sha, item.context_name, item.check_run_id): item
            for item in self.readbacks
        }
        if set(expected) != set(actual):
            raise ValueError("blocking readbacks do not cover the issued contexts")
        for key, context in expected.items():
            readback = actual[key]
            if (
                readback.app_integration_id != context.app_integration_id
                or readback.external_id != context.external_id
            ):
                raise ValueError("readback App/external identity changed")
        remaining_heads = set(self.intent.affected_head_shas) - {
            context.head_sha for context in self.issued_contexts
        }
        if {
            (proof.head_sha, proof.context_name, proof.app_integration_id)
            for proof in self.absence_proofs
        } != {
            (head, self.intent.required_context_name, self.intent.app_integration_id)
            for head in remaining_heads
        }:
            raise ValueError("absence proofs do not cover every unissued head")
        if any(
            proof.repository != self.repository or proof.goal_id != self.goal_id
            for proof in self.absence_proofs
        ):
            raise ValueError("absence proof refers to a different mutation scope")
        if self.scope_absence_proof is not None and (
            self.scope_absence_proof.repository != self.repository
            or self.scope_absence_proof.goal_id != self.goal_id
            or self.scope_absence_proof.intent_id != self.intent_id
            or self.scope_absence_proof.app_integration_id
            != self.intent.app_integration_id
            or self.scope_absence_proof.required_context_name
            != self.intent.required_context_name
            or self.scope_absence_proof.publication_store_revision
            != self.intent.publication_store_revision
            or self.scope_absence_proof.attempt_store_revision
            != self.intent.attempt_store_revision
        ):
            raise ValueError("scope-absence proof does not bind the mutation fences")
        if self.outcome == "complete_absence" and len(
            {(proof.head_sha, proof.context_name) for proof in self.absence_proofs}
        ) != len(self.absence_proofs):
            raise ValueError("complete-absence proofs must have unique head/context")
        if self.outcome == "all_blocked" and remaining_heads:
            raise ValueError(
                "all_blocked is missing absence proof for an affected head"
            )
        if self.outcome == "complete_absence" and self.readbacks:
            raise ValueError("complete_absence cannot contain blocked check runs")
        if self.outcome == "mixed" and not remaining_heads:
            raise ValueError("mixed confirmation has no absent head to prove")
        return self

    def content_sha256(self) -> str:
        payload = self.model_dump(mode="json", exclude={"confirmation_sha256"})
        payload["readbacks"] = sorted(
            payload["readbacks"],
            key=lambda readback: (
                readback["head_sha"],
                readback["context_name"],
                readback["check_run_id"],
            ),
        )
        payload["issued_contexts"] = sorted(
            payload["issued_contexts"],
            key=lambda context: (
                context["head_sha"],
                context["context_name"],
                context["check_run_id"],
            ),
        )
        payload["absence_proofs"] = sorted(
            payload["absence_proofs"],
            key=lambda proof: (proof["head_sha"], proof["context_name"]),
        )
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"

    @model_validator(mode="after")
    def _digest_matches_confirmation(self) -> Self:
        if self.content_sha256() != self.confirmation_sha256:
            raise ValueError("mutation confirmation digest mismatch")
        return self
