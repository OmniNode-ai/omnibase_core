# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalVerifierPolicy."""

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
from omnibase_core.models.validation.model_goal_criterion_baseline import (
    ModelGoalCriterionBaseline,
)
from omnibase_core.models.validation.model_goal_dependency_issuer_binding import (
    ModelGoalDependencyIssuerBinding,
)
from omnibase_core.models.validation.model_goal_subject_manifest import (
    ModelGoalSubjectManifest,
)


class ModelGoalVerifierPolicy(BaseModel):
    """Policy resolved from protected runtime configuration, never PR input."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: str
    goal_id: UUID
    contract_revision: UUID
    policy_revision: UUID
    issuer_domain: str = Field(..., min_length=1, max_length=128)
    verifier_artifact_sha256: str
    allowed_execution_identities: tuple[str, ...] = Field(..., min_length=1)
    max_attestation_age_seconds: int = Field(..., ge=1, le=86400)
    criterion_baseline: ModelGoalCriterionBaseline | None = None
    subject_manifest: ModelGoalSubjectManifest | None = None
    dependency_issuer_bindings: tuple[ModelGoalDependencyIssuerBinding, ...] = Field(
        default_factory=tuple
    )

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @field_validator("verifier_artifact_sha256")
    @classmethod
    def _verifier_digest_is_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError(
                "verifier artifact digest must use sha256:<64 lowercase hex>"
            )
        return value

    @field_validator("allowed_execution_identities")
    @classmethod
    def _execution_identities_are_unique(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("execution identities must be nonblank")
        if len(set(values)) != len(values):
            raise ValueError("execution identities must be unique")
        return values

    @model_validator(mode="after")
    def _dependency_issuers_are_unique(self) -> ModelGoalVerifierPolicy:
        dependency_ids = [
            binding.dependency_id for binding in self.dependency_issuer_bindings
        ]
        if len(set(dependency_ids)) != len(dependency_ids):
            raise ValueError("dependency issuer bindings must be unique")
        return self

    def content_sha256(self) -> str:
        """Hash the full immutable policy using canonical JSON serialization."""
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(payload).hexdigest()}"
