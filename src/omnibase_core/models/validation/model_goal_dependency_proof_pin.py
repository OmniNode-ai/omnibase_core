# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, contract-owned pins for cross-repository goal evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_goal_proof_kind import EnumGoalProofKind
from omnibase_core.enums.enum_goal_subject_kind import EnumGoalSubjectKind

if TYPE_CHECKING:
    from omnibase_core.models.validation.model_goal_evaluation_observation import (
        ModelGoalEvaluationObservation,
    )
    from omnibase_core.models.validation.model_goal_supervisor_attestation import (
        ModelGoalSupervisorAttestation,
    )


from omnibase_core.constants.constants_goal_admission import (
    _REPOSITORY_RE,
    _SHA256_RE,
)


class ModelGoalDependencyProofPin(BaseModel):
    """One named dependency pinned to exact signed evidence and artifacts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dependency_id: str = Field(  # string-id-ok: stable protected manifest key, not UUID
        ..., min_length=1, max_length=128
    )
    proof_kind: EnumGoalProofKind
    repository: str
    goal_id: UUID
    contract_revision: UUID
    contract_sha256: str
    subject_kind: EnumGoalSubjectKind
    subject_commit_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    subject_tree_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    attestation_id: UUID
    signed_attestation_sha256: str
    artifact_sha256: tuple[str, ...] = Field(..., min_length=1)

    @field_validator("dependency_id")
    @classmethod
    def _dependency_id_is_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("dependency_id must not be blank")
        return value

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @field_validator("contract_sha256", "signed_attestation_sha256")
    @classmethod
    def _required_digest_is_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("evidence digest must use sha256:<64 lowercase hex>")
        return value

    @field_validator("artifact_sha256")
    @classmethod
    def _artifacts_are_canonical(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not _SHA256_RE.fullmatch(value) for value in values):
            raise ValueError("artifact digests must use sha256:<64 lowercase hex>")
        if len(set(values)) != len(values):
            raise ValueError("artifact digests must be unique")
        return tuple(sorted(values))

    @model_validator(mode="after")
    def _proof_kind_matches_subject(self) -> Self:
        proof_subject_kind: dict[EnumGoalProofKind, EnumGoalSubjectKind] = {
            EnumGoalProofKind.COMMIT_CHECK: EnumGoalSubjectKind.COMMIT,
            EnumGoalProofKind.MERGE_GROUP_CHECK: EnumGoalSubjectKind.MERGE_GROUP,
            EnumGoalProofKind.MERGE_RESULT: EnumGoalSubjectKind.MERGE_GROUP,
            EnumGoalProofKind.DEPLOYMENT: EnumGoalSubjectKind.DEPLOYMENT,
        }
        expected_kind = proof_subject_kind.get(self.proof_kind)
        if expected_kind is not None and expected_kind != self.subject_kind:
            raise ValueError("proof kind does not match its pinned subject kind")
        return self

    def matches_signed_evidence(
        self,
        *,
        attestation: ModelGoalSupervisorAttestation,
        observation: ModelGoalEvaluationObservation,
    ) -> bool:
        """Cross-check this pin against typed evidence; signature trust is external."""
        return (
            self.attestation_id == attestation.attestation_id
            and self.signed_attestation_sha256 == attestation.content_sha256()
            and self.repository == attestation.repository
            and self.goal_id == attestation.goal_id
            and self.contract_revision == attestation.contract_revision
            and self.contract_sha256 == attestation.contract_sha256
            and self.subject_kind == observation.subject_kind
            and self.subject_commit_sha == attestation.subject_commit_sha
            and self.subject_tree_sha == attestation.subject_tree_sha
            and self.artifact_sha256 == attestation.attempt_artifact_sha256
            and attestation.binds_evaluation_observation(observation)
        )
