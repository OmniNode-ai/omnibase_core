# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result model for deterministic OCC merge eligibility."""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.enums.enum_goal_subject_kind import EnumGoalSubjectKind
from omnibase_core.enums.enum_occ_eligibility_reason import EnumOccEligibilityReason
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelOccEligibilityResult(BaseModel):
    """Replayable OCC eligibility decision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    eligible: bool
    reason: EnumOccEligibilityReason
    ticket_ids: tuple[str, ...] = Field(default_factory=tuple)
    occ_commit_sha: str | None = Field(default=None)
    contract_hashes: dict[str, str] = Field(default_factory=dict)
    receipt_ids: tuple[str, ...] = Field(default_factory=tuple)
    missing_contracts: tuple[str, ...] = Field(default_factory=tuple)
    missing_or_nonpass_receipts: tuple[str, ...] = Field(default_factory=tuple)
    stale_receipt_bindings: tuple[str, ...] = Field(default_factory=tuple)
    dependency_prs: tuple[str, ...] = Field(default_factory=tuple)
    detail: str = Field(default="")
    goal_id: UUID | None = Field(default=None)
    repository: str | None = Field(default=None)
    contract_revision: UUID | None = Field(default=None)
    contract_schema_version: ModelSemVer | None = Field(default=None)
    goal_contract_path: PurePosixPath | None = Field(default=None)
    goal_contract_source_commit_sha: str | None = Field(default=None)
    goal_contract_sha256: str | None = Field(default=None)
    goal_policy_revision: UUID | None = Field(default=None)
    goal_revision_history_store_revision: UUID | None = Field(default=None)
    subject_commit_sha: str | None = Field(default=None)
    subject_tree_sha: str | None = Field(default=None)
    attempt_id: UUID | None = Field(default=None)
    attempt_sequence: int | None = Field(default=None, ge=1)
    attempt_watermark_sequence: int | None = Field(default=None, ge=1)
    attempt_store_revision: UUID | None = Field(default=None)
    attempt_snapshot_sha256: str | None = Field(default=None)
    goal_revision_history_sha256: str | None = Field(default=None)
    criterion_baseline_sha256: str | None = Field(default=None)
    criterion_coverage_sha256: str | None = Field(default=None)
    evaluation_observation_id: UUID | None = Field(default=None)
    deadline_event_id: UUID | None = Field(default=None)
    evaluation_observed_at: AwareDatetime | None = Field(default=None)
    evaluation_observation_sha256: str | None = Field(default=None)
    evaluation_deadline_status: Literal["open", "expired"] | None = None
    evaluation_deadline_recorded_at: AwareDatetime | None = Field(default=None)
    evaluation_subject_kind: EnumGoalSubjectKind | None = None
    evaluation_merge_group_id: str | None = (
        Field(  # string-id-ok: GitHub merge-group identifier
            default=None
        )
    )
    evaluation_merge_group_base_sha: str | None = Field(default=None)
    evaluation_merge_group_head_sha: str | None = Field(default=None)
    evaluation_deployment_id: str | None = (
        Field(  # string-id-ok: deployment provider identifier
            default=None
        )
    )
    evaluation_environment_id: str | None = (
        Field(  # string-id-ok: protected environment key
            default=None
        )
    )
    evaluation_runtime_instance_id: str | None = (
        Field(  # string-id-ok: runtime provider identifier
            default=None
        )
    )
    evaluation_artifact_sha256: str | None = Field(default=None)
    evaluation_runtime_config_sha256: str | None = Field(default=None)
    goal_mutation_store_revision: UUID | None = Field(default=None)
    goal_mutation_state_sha256: str | None = Field(default=None)
    goal_mutation_intent_id: UUID | None = Field(default=None)

    @field_serializer(
        "contract_schema_version", when_used="json", return_type=str | None
    )
    def _serialize_contract_schema_version(
        self, value: ModelSemVer | None
    ) -> str | None:
        return value.to_string() if value is not None else None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "eligible": self.eligible,
            "reason": self.reason.value,
            "ticket_ids": sorted(self.ticket_ids),
            "occ_commit_sha": self.occ_commit_sha,
            "contract_hashes": dict(sorted(self.contract_hashes.items())),
            "receipt_ids": sorted(self.receipt_ids),
            "missing_contracts": sorted(self.missing_contracts),
            "missing_or_nonpass_receipts": sorted(self.missing_or_nonpass_receipts),
            "stale_receipt_bindings": sorted(self.stale_receipt_bindings),
            "dependency_prs": sorted(self.dependency_prs, key=str),
            "detail": self.detail,
        }
        goal_fields: dict[str, object | None] = {
            "goal_id": str(self.goal_id) if self.goal_id is not None else None,
            "repository": self.repository,
            "contract_revision": (
                str(self.contract_revision)
                if self.contract_revision is not None
                else None
            ),
            "contract_schema_version": (
                self.contract_schema_version.to_string()
                if self.contract_schema_version is not None
                else None
            ),
            "goal_contract_path": (
                str(self.goal_contract_path)
                if self.goal_contract_path is not None
                else None
            ),
            "goal_contract_source_commit_sha": self.goal_contract_source_commit_sha,
            "goal_contract_sha256": self.goal_contract_sha256,
            "goal_policy_revision": (
                str(self.goal_policy_revision)
                if self.goal_policy_revision is not None
                else None
            ),
            "goal_revision_history_store_revision": (
                str(self.goal_revision_history_store_revision)
                if self.goal_revision_history_store_revision is not None
                else None
            ),
            "subject_commit_sha": self.subject_commit_sha,
            "subject_tree_sha": self.subject_tree_sha,
            "attempt_id": str(self.attempt_id) if self.attempt_id is not None else None,
            "attempt_sequence": self.attempt_sequence,
            "attempt_watermark_sequence": self.attempt_watermark_sequence,
            "attempt_store_revision": (
                str(self.attempt_store_revision)
                if self.attempt_store_revision is not None
                else None
            ),
            "attempt_snapshot_sha256": self.attempt_snapshot_sha256,
            "goal_revision_history_sha256": self.goal_revision_history_sha256,
            "criterion_baseline_sha256": self.criterion_baseline_sha256,
            "criterion_coverage_sha256": self.criterion_coverage_sha256,
            "evaluation_observation_id": (
                str(self.evaluation_observation_id)
                if self.evaluation_observation_id is not None
                else None
            ),
            "deadline_event_id": (
                str(self.deadline_event_id)
                if self.deadline_event_id is not None
                else None
            ),
            "evaluation_observed_at": (
                self.evaluation_observed_at.isoformat()
                if self.evaluation_observed_at is not None
                else None
            ),
            "evaluation_observation_sha256": self.evaluation_observation_sha256,
            "evaluation_deadline_status": self.evaluation_deadline_status,
            "evaluation_deadline_recorded_at": (
                self.evaluation_deadline_recorded_at.isoformat()
                if self.evaluation_deadline_recorded_at is not None
                else None
            ),
            "evaluation_subject_kind": (
                self.evaluation_subject_kind.value
                if self.evaluation_subject_kind is not None
                else None
            ),
            "evaluation_merge_group_id": self.evaluation_merge_group_id,
            "evaluation_merge_group_base_sha": self.evaluation_merge_group_base_sha,
            "evaluation_merge_group_head_sha": self.evaluation_merge_group_head_sha,
            "evaluation_deployment_id": self.evaluation_deployment_id,
            "evaluation_environment_id": self.evaluation_environment_id,
            "evaluation_runtime_instance_id": self.evaluation_runtime_instance_id,
            "evaluation_artifact_sha256": self.evaluation_artifact_sha256,
            "evaluation_runtime_config_sha256": self.evaluation_runtime_config_sha256,
            "goal_mutation_store_revision": (
                str(self.goal_mutation_store_revision)
                if self.goal_mutation_store_revision is not None
                else None
            ),
            "goal_mutation_state_sha256": self.goal_mutation_state_sha256,
            "goal_mutation_intent_id": (
                str(self.goal_mutation_intent_id)
                if self.goal_mutation_intent_id is not None
                else None
            ),
        }
        result.update(
            {key: value for key, value in goal_fields.items() if value is not None}
        )
        return result

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


__all__ = ["ModelOccEligibilityResult"]
