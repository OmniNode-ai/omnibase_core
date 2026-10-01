# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protected observation made while evaluating completed goal evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.constants.constants_goal_admission import (
    _REPOSITORY_RE,
    _SHA256_RE,
)


class ModelGoalAdmissionObservation(BaseModel):
    """Trusted post-execution time and exact evidence bindings for admission.

    This record is durably stored as a content-addressed artifact before it is
    returned by the protected admission store. It is distinct from the initial
    observation that defines the goal deadline and is never sourced from
    candidate-controlled contract or receipt data.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    observation_id: UUID
    repository: str
    goal_id: UUID
    contract_revision: UUID
    subject_commit_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    subject_tree_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    attempt_id: UUID
    attempt_sequence: int = Field(..., ge=1)
    attempt_store_revision: UUID
    attempt_snapshot_sha256: str
    contract_sha256: str
    execution_record_id: UUID
    execution_receipt_sha256: str
    attestation_id: UUID
    attestation_sha256: str
    policy_revision: UUID
    policy_sha256: str
    verifier_artifact_sha256: str
    criterion_baseline_sha256: str
    criterion_coverage_sha256: str
    revision_history_sha256: str
    evaluation_observation_id: UUID
    evaluation_observation_sha256: str
    deadline_event_id: UUID
    deadline_at: datetime
    observed_at: datetime

    @field_validator("repository")
    @classmethod
    def _repository_is_canonical(cls, value: str) -> str:
        if not _REPOSITORY_RE.fullmatch(value):
            raise ValueError("repository must be canonical owner/repository")
        return value

    @field_validator(
        "attempt_snapshot_sha256",
        "contract_sha256",
        "execution_receipt_sha256",
        "attestation_sha256",
        "policy_sha256",
        "verifier_artifact_sha256",
        "criterion_baseline_sha256",
        "criterion_coverage_sha256",
        "revision_history_sha256",
        "evaluation_observation_sha256",
    )
    @classmethod
    def _digest_is_canonical(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("digest must use sha256:<64 lowercase hex>")
        return value

    @model_validator(mode="after")
    def _timestamps_are_ordered(self) -> ModelGoalAdmissionObservation:
        for name, value in (
            ("deadline_at", self.deadline_at),
            ("observed_at", self.observed_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must include a timezone")
        if self.observed_at > self.deadline_at:
            raise ValueError("admission observation cannot occur after its deadline")
        return self

    def canonical_json(self) -> str:
        """Return the exact canonical payload used by the evidence store."""
        return json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )

    def content_sha256(self) -> str:
        """Identify the immutable, replayable admission-observation payload."""
        return f"sha256:{hashlib.sha256(self.canonical_json().encode('utf-8')).hexdigest()}"


__all__ = ["ModelGoalAdmissionObservation"]
