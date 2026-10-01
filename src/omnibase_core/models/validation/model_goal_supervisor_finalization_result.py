# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGoalSupervisorFinalizationResult contract model."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.enum_goal_attempt_status import EnumGoalAttemptStatus
from omnibase_core.enums.enum_goal_supervisor_outcome import EnumGoalSupervisorOutcome
from omnibase_core.models.validation.model_goal_attempt_allocation_snapshot import (
    ModelGoalAttemptAllocationSnapshot,
)
from omnibase_core.models.validation.model_goal_supervisor_attestation import (
    ModelGoalSupervisorAttestation,
)
from omnibase_core.models.validation.model_goal_supervisor_finalization_request import (
    ModelGoalSupervisorFinalizationRequest,
)


class ModelGoalSupervisorFinalizationResult(BaseModel):
    """Final attestation bound to the supervisor's post-persist store readback."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    finalization: ModelGoalSupervisorFinalizationRequest
    completed_attempt_snapshot: ModelGoalAttemptAllocationSnapshot
    attestation: ModelGoalSupervisorAttestation
    trusted_observation_id: UUID

    @model_validator(mode="after")
    def _attestation_binds_completed_store_readback(
        self,
    ) -> ModelGoalSupervisorFinalizationResult:
        execution = self.finalization.execution
        request = execution.request
        snapshot = self.completed_attempt_snapshot
        attempt = max(snapshot.attempts, key=lambda item: item.sequence)
        attestation = self.attestation
        baseline = request.policy.criterion_baseline
        if baseline is None:
            raise ValueError("protected criterion baseline is required")
        expected_status = (
            EnumGoalAttemptStatus.PASS
            if execution.outcome is EnumGoalSupervisorOutcome.PASS
            else EnumGoalAttemptStatus.FAIL
        )
        if execution.outcome not in {
            EnumGoalSupervisorOutcome.PASS,
            EnumGoalSupervisorOutcome.FAIL,
        }:
            raise ValueError("only terminal PASS or FAIL executions can be finalized")
        if (
            snapshot.repository != request.attempt_snapshot.repository
            or snapshot.goal_id != request.attempt_snapshot.goal_id
            or snapshot.contract_revision != request.attempt_snapshot.contract_revision
            or snapshot.subject_commit_sha
            != request.attempt_snapshot.subject_commit_sha
            or snapshot.subject_tree_sha != request.attempt_snapshot.subject_tree_sha
            or snapshot.store_revision == request.attempt_snapshot.store_revision
            or attempt.attempt_id != request.attempt_id
            or attempt.sequence != request.attempt_sequence
            or attempt.status is not expected_status
            or attempt.result_sha256 != execution.result.content_sha256()
            or tuple(sorted(attempt.artifact_sha256))
            != execution.result.artifact_sha256
        ):
            raise ValueError(
                "supervisor store readback does not contain this execution"
            )
        if (
            attestation.attempt_id != attempt.attempt_id
            or attestation.attempt_sequence != attempt.sequence
            or attestation.attempt_store_revision != snapshot.store_revision
            or attestation.attempt_snapshot_sha256 != snapshot.snapshot_sha256
            or attestation.execution_record_id
            != execution.execution_receipt.execution_record_id
            or attestation.execution_receipt_sha256
            != execution.execution_receipt.content_sha256()
            or attestation.attempt_result_sha256 != attempt.result_sha256
            or tuple(sorted(attestation.attempt_artifact_sha256))
            != tuple(sorted(attempt.artifact_sha256))
            or attestation.evaluation_observation_id
            != request.evaluation_observation.observation_id
            or attestation.deadline_event_id
            != request.evaluation_observation.deadline_event_id
            or attestation.goal_id != request.attempt_snapshot.goal_id
            or attestation.repository != request.attempt_snapshot.repository
            or attestation.contract_revision
            != request.attempt_snapshot.contract_revision
            or attestation.contract_schema_version
            != request.contract.contract_schema_version
            or attestation.contract_path != request.contract.contract_path
            or attestation.contract_source_commit_sha
            != request.contract.contract_source_commit_sha
            or attestation.contract_sha256 != request.contract.contract_sha256
            or attestation.subject_commit_sha
            != request.attempt_snapshot.subject_commit_sha
            or attestation.subject_tree_sha != request.attempt_snapshot.subject_tree_sha
            or attestation.verifier_artifact_sha256
            != request.policy.verifier_artifact_sha256
            or attestation.policy_revision != request.policy.policy_revision
            or attestation.policy_sha256 != request.policy.content_sha256()
            or attestation.issuer_domain != request.policy.issuer_domain
            or attestation.execution_identity
            not in request.policy.allowed_execution_identities
            or attestation.criterion_baseline_sha256 != baseline.content_sha256()
            or attestation.revision_history_sha256
            != request.revision_history.snapshot_sha256
            or self.trusted_observation_id
            != request.evaluation_observation.observation_id
        ):
            raise ValueError(
                "final attestation does not bind the post-persist snapshot"
            )
        return self
