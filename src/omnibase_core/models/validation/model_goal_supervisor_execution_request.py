# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGoalSupervisorExecutionRequest contract model."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_goal_attempt_status import EnumGoalAttemptStatus
from omnibase_core.errors import OnexError
from omnibase_core.models.validation.model_goal_attempt_allocation_snapshot import (
    ModelGoalAttemptAllocationSnapshot,
)
from omnibase_core.models.validation.model_goal_contract_revision_record import (
    ModelGoalContractRevisionRecord,
)
from omnibase_core.models.validation.model_goal_evaluation_observation import (
    ModelGoalEvaluationObservation,
)
from omnibase_core.models.validation.model_goal_revision_history_snapshot import (
    ModelGoalRevisionHistorySnapshot,
)
from omnibase_core.models.validation.model_goal_verifier_policy import (
    ModelGoalVerifierPolicy,
)
from omnibase_core.utils.util_goal_verification import (
    compute_goal_execution_request_sha256,
)


class ModelGoalSupervisorExecutionRequest(BaseModel):
    """Protected execution inputs and the already allocated attempt.

    Callers provide typed source, subject, policy, and attempt facts only. The
    request intentionally has no command, selector, image, environment, key,
    or output-path field. The supervisor resolves all execution details from
    the protected verifier policy and release registry.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract: ModelGoalContractRevisionRecord
    attempt_snapshot: ModelGoalAttemptAllocationSnapshot
    policy: ModelGoalVerifierPolicy
    evaluation_observation: ModelGoalEvaluationObservation
    revision_history: ModelGoalRevisionHistorySnapshot
    dispatch_idempotency_key: UUID

    @model_validator(mode="after")
    def _all_sources_bind_to_one_allocated_attempt(
        self,
    ) -> ModelGoalSupervisorExecutionRequest:
        snapshot = self.attempt_snapshot
        contract = self.contract
        policy = self.policy
        observation = self.evaluation_observation
        history = self.revision_history
        selected = max(snapshot.attempts, key=lambda attempt: attempt.sequence)

        if selected.sequence != snapshot.watermark_sequence:
            raise ValueError("execution must target the highest allocated attempt")
        if selected.status is not EnumGoalAttemptStatus.RUNNING:
            raise ValueError("execution requires the durable RUNNING attempt snapshot")
        if self.dispatch_idempotency_key != selected.attempt_id:
            raise ValueError(
                "dispatch idempotency key must equal the allocated attempt id"
            )

        subject = (
            snapshot.repository,
            snapshot.goal_id,
            snapshot.contract_revision,
            snapshot.subject_commit_sha,
            snapshot.subject_tree_sha,
        )
        if (contract.repository, contract.goal_id, contract.revision_id) != subject[:3]:
            raise ValueError("contract source does not match the allocated subject")
        if (
            policy.repository,
            policy.goal_id,
            policy.contract_revision,
        ) != subject[:3]:
            raise ValueError("protected policy does not match the allocated subject")
        if (
            observation.repository,
            observation.goal_id,
            observation.contract_revision,
            observation.subject_commit_sha,
            observation.subject_tree_sha,
        ) != subject:
            raise ValueError(
                "recorded observation does not match the allocated subject"
            )
        history_contract = next(
            (
                revision
                for revision in history.revisions
                if revision.revision_id == contract.revision_id
            ),
            None,
        )
        if (
            history.repository != snapshot.repository
            or history.goal_id != snapshot.goal_id
            or history_contract != contract
            or history.content_sha256() != history.snapshot_sha256
        ):
            raise ValueError("revision history does not match the allocated goal")
        if policy.criterion_baseline is None:
            raise ValueError("protected criterion baseline is required for execution")
        manifest = policy.subject_manifest
        if manifest is None:
            raise ValueError("protected subject manifest is required for execution")
        manifest.validate_observation_subject(observation)
        manifest.validate_for_owner(
            repository=snapshot.repository, goal_id=snapshot.goal_id
        )
        if selected.execution_request_sha256 != self.execution_plan_sha256():
            raise ValueError(
                "allocated attempt differs from the immutable execution plan"
            )
        return self

    @property
    def attempt_id(self) -> UUID:
        """Allocated idempotent attempt identity selected by the request."""
        return max(
            self.attempt_snapshot.attempts, key=lambda item: item.sequence
        ).attempt_id

    @property
    def attempt_sequence(self) -> int:
        """Highest allocated attempt sequence selected by the request."""
        return max(
            self.attempt_snapshot.attempts, key=lambda item: item.sequence
        ).sequence

    def execution_plan_sha256(self) -> str:
        """Digest protected immutable plan inputs, excluding the RUNNING snapshot."""
        manifest = self.policy.subject_manifest
        baseline = self.policy.criterion_baseline
        if manifest is None or baseline is None:
            raise OnexError(
                message="protected manifest and criterion baseline are required",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return compute_goal_execution_request_sha256(
            repository=self.attempt_snapshot.repository,
            goal_id=self.attempt_snapshot.goal_id,
            contract_revision=self.contract.revision_id,
            contract_sha256=self.contract.contract_sha256,
            policy_revision=self.policy.policy_revision,
            policy_sha256=self.policy.content_sha256(),
            verifier_artifact_sha256=self.policy.verifier_artifact_sha256,
            criterion_baseline_sha256=baseline.content_sha256(),
            revision_history_sha256=self.revision_history.snapshot_sha256,
            evaluation_observation_sha256=self.evaluation_observation.content_sha256(),
            subject_manifest_sha256=manifest.content_sha256(),
            attempt_id=self.attempt_id,
            attempt_sequence=self.attempt_sequence,
            subject_kind=self.evaluation_observation.subject_kind,
            subject_commit_sha=self.attempt_snapshot.subject_commit_sha,
            subject_tree_sha=self.attempt_snapshot.subject_tree_sha,
        )
