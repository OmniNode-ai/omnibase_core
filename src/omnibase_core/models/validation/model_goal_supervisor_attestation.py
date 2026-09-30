# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalSupervisorAttestation."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import PurePosixPath
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from omnibase_core.constants.constants_goal_admission import (
    _REPOSITORY_RE,
    _SHA256_RE,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.validation.model_goal_evaluation_observation import (
    ModelGoalEvaluationObservation,
)


class ModelGoalSupervisorAttestation(BaseModel):
    """Signed evidence issued by the trusted supervisor after isolated checks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attestation_id: UUID
    issuer_domain: str = Field(..., min_length=1, max_length=128)
    goal_id: UUID
    repository: str
    contract_revision: UUID
    contract_schema_version: ModelSemVer
    contract_path: PurePosixPath
    contract_source_commit_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    contract_sha256: str
    subject_commit_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    subject_tree_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    attempt_id: UUID
    attempt_sequence: int = Field(..., ge=1)
    execution_record_id: UUID
    execution_receipt_sha256: str
    attempt_result_sha256: str
    attempt_artifact_sha256: tuple[str, ...] = Field(default_factory=tuple)
    subject_manifest_sha256: str
    evaluation_observation_sha256: str
    attempt_store_revision: UUID
    attempt_snapshot_sha256: str
    criterion_baseline_sha256: str
    criterion_coverage_sha256: str
    revision_history_sha256: str
    evaluation_observation_id: UUID
    deadline_event_id: UUID
    verifier_artifact_sha256: str
    policy_revision: UUID
    execution_identity: str = Field(..., min_length=1, max_length=256)
    issued_at: datetime
    expires_at: datetime
    signature: str = Field(..., min_length=1)

    @field_validator(
        "contract_schema_version", mode="before", json_schema_input_type=str
    )
    @classmethod
    def _schema_version_is_valid(cls, value: object) -> ModelSemVer:
        # Keep this import local: ``omnibase_core.utils`` initializes the
        # package bootstrap, which itself imports public protocols/models.
        from omnibase_core.utils.util_contract_schema_version import (
            validate_contract_schema_version,
        )

        if isinstance(value, ModelSemVer):
            validate_contract_schema_version(value.to_string())
            return value
        if not isinstance(value, str):
            raise ValueError("contract_schema_version must be a SemVer string")
        validate_contract_schema_version(value)
        return ModelSemVer.parse(value)

    @field_serializer("contract_schema_version", when_used="json", return_type=str)
    def _serialize_schema_version(self, value: ModelSemVer) -> str:
        return value.to_string()

    @field_validator(
        "contract_sha256",
        "attempt_result_sha256",
        "attempt_snapshot_sha256",
        "execution_receipt_sha256",
        "subject_manifest_sha256",
        "evaluation_observation_sha256",
        "criterion_baseline_sha256",
        "criterion_coverage_sha256",
        "revision_history_sha256",
        "verifier_artifact_sha256",
    )
    @classmethod
    def _required_digests_are_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("digest must use sha256:<64 lowercase hex>")
        return value

    @field_validator("attempt_artifact_sha256")
    @classmethod
    def _artifact_digests_are_canonical(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        if any(not _SHA256_RE.fullmatch(value) for value in values):
            raise ValueError("artifact digests must use sha256:<64 lowercase hex>")
        if len(set(values)) != len(values):
            raise ValueError("artifact digests must be unique")
        return tuple(sorted(values))

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @model_validator(mode="after")
    def _validate_utc_window(self) -> ModelGoalSupervisorAttestation:
        if self.issued_at.tzinfo is None or self.issued_at.utcoffset() is None:
            raise ValueError("issued_at must include a timezone")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("expires_at must include a timezone")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if self.contract_path.is_absolute() or ".." in self.contract_path.parts:
            raise ValueError("contract_path must be a repository-relative path")
        if self.contract_path.parts[:2] != ("contracts", "goals"):
            raise ValueError("contract_path must be under contracts/goals/")
        return self

    def signing_payload(self) -> bytes:
        """Canonical UTF-8 payload covered by the supervisor signature."""
        payload = self.model_dump(mode="json", exclude={"signature"})
        payload["attempt_artifact_sha256"] = sorted(self.attempt_artifact_sha256)
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )

    def content_sha256(self) -> str:
        """Digest the signed attestation for exact dependency-pin binding."""
        payload = self.model_dump(mode="json")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"

    def binds_evaluation_observation(
        self, observation: ModelGoalEvaluationObservation
    ) -> bool:
        """Return whether this attestation binds the exact recorded observation."""
        return (
            self.evaluation_observation_id == observation.observation_id
            and self.deadline_event_id == observation.deadline_event_id
            and self.evaluation_observation_sha256 == observation.content_sha256()
            and self.repository == observation.repository
            and self.goal_id == observation.goal_id
            and self.contract_revision == observation.contract_revision
            and self.subject_commit_sha == observation.subject_commit_sha
            and self.subject_tree_sha == observation.subject_tree_sha
        )

    def is_fresh_at(self, now: datetime, *, max_age_seconds: int) -> bool:
        """Return whether this signed attestation is current under its policy."""
        if now.tzinfo is None or now.utcoffset() is None:
            return False
        issued = self.issued_at.astimezone(UTC)
        current = now.astimezone(UTC)
        expires = self.expires_at.astimezone(UTC)
        age_seconds = (current - issued).total_seconds()
        return issued <= current < expires and 0 <= age_seconds <= max_age_seconds
