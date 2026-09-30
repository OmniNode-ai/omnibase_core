# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal attempt model: ModelGoalAttemptAllocationSnapshot."""

from __future__ import annotations

import hashlib
import json
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
)
from omnibase_core.models.validation.model_goal_verification_attempt import (
    ModelGoalVerificationAttempt,
)


class ModelGoalAttemptAllocationSnapshot(BaseModel):
    """Complete immutable allocation view for one exact goal subject."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    goal_id: UUID
    repository: str = Field(..., min_length=3)
    contract_revision: UUID
    subject_commit_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    subject_tree_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    allocation_count: PositiveInt
    watermark_sequence: PositiveInt
    store_revision: UUID
    attempts: tuple[ModelGoalVerificationAttempt, ...] = Field(..., min_length=1)
    snapshot_sha256: str = Field(..., pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("repository")
    @classmethod
    def _canonical_repository(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @model_validator(mode="after")
    def _validate_complete_partition(self) -> ModelGoalAttemptAllocationSnapshot:
        if self.allocation_count != len(self.attempts):
            raise ValueError("allocation_count must equal the complete attempt tuple")
        if self.watermark_sequence != self.allocation_count:
            raise ValueError(
                "watermark_sequence must equal the highest allocated sequence"
            )
        sequences = [attempt.sequence for attempt in self.attempts]
        if sorted(sequences) != list(range(1, self.watermark_sequence + 1)):
            raise ValueError(
                "allocation snapshot must include every sequence through watermark"
            )
        if len({attempt.attempt_id for attempt in self.attempts}) != len(self.attempts):
            raise ValueError("allocation snapshot contains duplicate attempt_id values")
        for attempt in self.attempts:
            if (
                attempt.goal_id != self.goal_id
                or attempt.repository != self.repository
                or attempt.contract_revision != self.contract_revision
                or attempt.subject_commit_sha != self.subject_commit_sha
                or attempt.subject_tree_sha != self.subject_tree_sha
            ):
                raise ValueError("attempt row does not match the snapshot partition")
        if self.snapshot_sha256 != self.compute_snapshot_sha256(
            goal_id=self.goal_id,
            repository=self.repository,
            contract_revision=self.contract_revision,
            subject_commit_sha=self.subject_commit_sha,
            subject_tree_sha=self.subject_tree_sha,
            allocation_count=self.allocation_count,
            watermark_sequence=self.watermark_sequence,
            store_revision=self.store_revision,
            attempts=self.attempts,
        ):
            raise ValueError("allocation snapshot digest does not match its contents")
        return self

    @staticmethod
    def compute_snapshot_sha256(
        *,
        goal_id: UUID,
        repository: str,
        contract_revision: UUID,
        subject_commit_sha: str,
        subject_tree_sha: str,
        allocation_count: int,
        watermark_sequence: int,
        store_revision: UUID,
        attempts: tuple[ModelGoalVerificationAttempt, ...],
    ) -> str:
        """Return the canonical digest for one full allocation snapshot."""
        payload = {
            "goal_id": str(goal_id),
            "repository": repository,
            "contract_revision": str(contract_revision),
            "subject_commit_sha": subject_commit_sha,
            "subject_tree_sha": subject_tree_sha,
            "allocation_count": allocation_count,
            "watermark_sequence": watermark_sequence,
            "store_revision": str(store_revision),
            "attempts": [
                attempt.model_dump(mode="json")
                for attempt in sorted(attempts, key=lambda item: item.sequence)
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
