# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalSupervisorExecutionReceipt."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
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


class ModelGoalSupervisorExecutionReceipt(BaseModel):
    """Supervisor-signed immutable output from one isolated verifier execution.

    This receipt binds the executor's result before Market stores its terminal
    status. It is distinct from ``ModelGoalSupervisorAttestation``, which is
    issued only after the durable PASS snapshot exists.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_record_id: UUID
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
    running_attempt_store_revision: UUID
    running_attempt_snapshot_sha256: str
    execution_request_sha256: str
    result_sha256: str
    artifact_sha256: tuple[str, ...] = Field(default_factory=tuple)
    subject_manifest_sha256: str
    evaluation_observation_sha256: str
    verifier_artifact_sha256: str
    policy_revision: UUID
    execution_identity: str = Field(..., min_length=1, max_length=256)
    started_at: datetime
    completed_at: datetime
    signature: str = Field(..., min_length=1)

    @field_validator(
        "contract_sha256",
        "running_attempt_snapshot_sha256",
        "execution_request_sha256",
        "result_sha256",
        "subject_manifest_sha256",
        "evaluation_observation_sha256",
        "verifier_artifact_sha256",
    )
    @classmethod
    def _receipt_digests_are_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError(
                "execution receipt digests require sha256:<64 lowercase hex>"
            )
        return value

    @field_validator("artifact_sha256")
    @classmethod
    def _receipt_artifacts_are_canonical(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        if any(not _SHA256_RE.fullmatch(value) for value in values):
            raise ValueError(
                "execution artifact digests require sha256:<64 lowercase hex>"
            )
        if len(set(values)) != len(values):
            raise ValueError("execution artifact digests must be unique")
        return tuple(sorted(values))

    @field_validator("repository")
    @classmethod
    def _receipt_repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @field_validator(
        "contract_schema_version", mode="before", json_schema_input_type=str
    )
    @classmethod
    def _receipt_schema_version_is_valid(cls, value: object) -> ModelSemVer:
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
    def _serialize_receipt_schema_version(self, value: ModelSemVer) -> str:
        return value.to_string()

    @model_validator(mode="after")
    def _receipt_time_and_contract_path_are_valid(
        self,
    ) -> ModelGoalSupervisorExecutionReceipt:
        for name, value in (
            ("started_at", self.started_at),
            ("completed_at", self.completed_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must include a timezone")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        if (
            self.contract_path.is_absolute()
            or ".." in self.contract_path.parts
            or self.contract_path.parts[:2] != ("contracts", "goals")
        ):
            raise ValueError(
                "contract_path must be repository-relative under contracts/goals/"
            )
        return self

    def signing_payload(self) -> bytes:
        """Canonical result/request bytes authenticated by the supervisor."""
        payload = self.model_dump(mode="json", exclude={"signature"})
        payload["artifact_sha256"] = sorted(self.artifact_sha256)
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )

    def content_sha256(self) -> str:
        """Digest the signed receipt for final-attestation linkage."""
        canonical = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
