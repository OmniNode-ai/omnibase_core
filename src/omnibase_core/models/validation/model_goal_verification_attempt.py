# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal attempt model: ModelGoalVerificationAttempt."""

from __future__ import annotations

from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    field_validator,
    model_validator,
)

from omnibase_core.constants.constants_goal_admission import (
    _REPOSITORY_RE,
    _SHA256_RE,
)
from omnibase_core.enums.enum_goal_attempt_status import EnumGoalAttemptStatus


class ModelGoalVerificationAttempt(BaseModel):
    """One allocation and its latest immutable outcome for a goal subject."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    goal_id: UUID
    repository: str = Field(..., min_length=3)
    contract_revision: UUID
    subject_commit_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    subject_tree_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    attempt_id: UUID
    sequence: PositiveInt
    status: EnumGoalAttemptStatus
    execution_request_sha256: str
    running_store_revision: UUID | None = None
    running_snapshot_sha256: str | None = None
    result_sha256: str | None = None
    artifact_sha256: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("repository")
    @classmethod
    def _canonical_repository(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @field_validator("result_sha256")
    @classmethod
    def _result_digest(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256_RE.fullmatch(value):
            raise ValueError("result_sha256 must use sha256:<64 lowercase hex>")
        return value

    @field_validator("execution_request_sha256", "running_snapshot_sha256")
    @classmethod
    def _execution_snapshot_digest(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256_RE.fullmatch(value):
            raise ValueError(
                "execution snapshot digests require sha256:<64 lowercase hex>"
            )
        return value

    @field_validator("artifact_sha256")
    @classmethod
    def _artifact_digests(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not _SHA256_RE.fullmatch(value) for value in values):
            raise ValueError("artifact digests must use sha256:<64 lowercase hex>")
        if len(set(values)) != len(values):
            raise ValueError("artifact digests must be unique")
        return values

    @model_validator(mode="after")
    def _pass_requires_result(self) -> ModelGoalVerificationAttempt:
        if self.status is EnumGoalAttemptStatus.PASS:
            if self.result_sha256 is None:
                raise ValueError("a PASS attempt requires an immutable result digest")
            if (
                self.running_store_revision is None
                or self.running_snapshot_sha256 is None
            ):
                raise ValueError(
                    "a PASS attempt requires its persisted RUNNING snapshot"
                )
        if (self.running_store_revision is None) != (
            self.running_snapshot_sha256 is None
        ):
            raise ValueError("RUNNING snapshot revision and digest must be paired")
        return self
