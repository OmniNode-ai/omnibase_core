# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalEvaluationObservation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal
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
from omnibase_core.enums.enum_goal_subject_kind import EnumGoalSubjectKind


class ModelGoalEvaluationObservation(BaseModel):
    """Trusted recorded observation and deadline used to evaluate freshness."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    observation_id: UUID
    deadline_event_id: UUID
    repository: str
    goal_id: UUID
    contract_revision: UUID
    subject_commit_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    subject_tree_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    subject_kind: EnumGoalSubjectKind = EnumGoalSubjectKind.COMMIT
    merge_group_id: str | None = Field(  # string-id-ok: GitHub merge-group identifier
        default=None, min_length=1, max_length=256
    )
    merge_group_base_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    merge_group_head_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    deployment_id: str | None = Field(  # string-id-ok: deployment provider identifier
        default=None, min_length=1, max_length=256
    )
    environment_id: str | None = Field(  # string-id-ok: protected environment key
        default=None, min_length=1, max_length=128
    )
    runtime_instance_id: str | None = (
        Field(  # string-id-ok: runtime provider identifier
            default=None, min_length=1, max_length=256
        )
    )
    artifact_sha256: str | None = None
    runtime_config_sha256: str | None = None
    observed_at: datetime
    deadline_at: datetime
    deadline_status: Literal["open", "expired"] = "open"
    deadline_recorded_at: datetime | None = None

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @model_validator(mode="after")
    def _times_are_aware_and_ordered(self) -> ModelGoalEvaluationObservation:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        if self.deadline_at.tzinfo is None or self.deadline_at.utcoffset() is None:
            raise ValueError("deadline_at must include a timezone")
        if self.deadline_at < self.observed_at:
            raise ValueError("deadline_at cannot precede the recorded observation")
        if self.deadline_status == "open":
            if self.deadline_recorded_at is not None:
                raise ValueError("open deadline cannot have a recorded expiry time")
        else:
            if self.deadline_recorded_at is None:
                raise ValueError(
                    "expired deadline requires its persisted occurrence time"
                )
            if (
                self.deadline_recorded_at.tzinfo is None
                or self.deadline_recorded_at.utcoffset() is None
            ):
                raise ValueError("deadline_recorded_at must include a timezone")
            if self.deadline_recorded_at < self.deadline_at:
                raise ValueError("deadline occurrence cannot precede its deadline")
        if self.subject_kind == "commit":
            if any(
                value is not None
                for value in (
                    self.merge_group_id,
                    self.merge_group_base_sha,
                    self.merge_group_head_sha,
                    self.deployment_id,
                    self.environment_id,
                    self.runtime_instance_id,
                    self.artifact_sha256,
                    self.runtime_config_sha256,
                )
            ):
                raise ValueError(
                    "commit observation cannot carry merge/deployment fields"
                )
        elif self.subject_kind == "merge_group":
            if not all(
                (
                    self.merge_group_id,
                    self.merge_group_base_sha,
                    self.merge_group_head_sha,
                )
            ) or any(
                value is not None
                for value in (
                    self.deployment_id,
                    self.environment_id,
                    self.runtime_instance_id,
                    self.artifact_sha256,
                    self.runtime_config_sha256,
                )
            ):
                raise ValueError(
                    "merge-group observation requires exact group/base/head"
                )
        elif self.subject_kind == "deployment":
            if not all(
                (
                    self.deployment_id,
                    self.environment_id,
                    self.runtime_instance_id,
                    self.artifact_sha256,
                    self.runtime_config_sha256,
                )
            ) or any(
                value is not None
                for value in (
                    self.merge_group_id,
                    self.merge_group_base_sha,
                    self.merge_group_head_sha,
                )
            ):
                raise ValueError(
                    "deployment observation requires artifact/runtime identity"
                )
        for name in ("artifact_sha256", "runtime_config_sha256"):
            value = getattr(self, name)
            if value is not None and not _SHA256_RE.fullmatch(value):
                raise ValueError(f"{name} must use sha256:<64 lowercase hex>")
        return self

    def content_sha256(self) -> str:
        """Digest the complete protected observation and deadline binding."""
        canonical = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
