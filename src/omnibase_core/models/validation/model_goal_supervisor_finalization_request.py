# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGoalSupervisorFinalizationRequest contract model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.models.validation.model_goal_supervisor_execution_result import (
    ModelGoalSupervisorExecutionResult,
)


class ModelGoalSupervisorFinalizationRequest(BaseModel):
    """Request the supervisor to independently read the completed attempt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    execution: ModelGoalSupervisorExecutionResult

    @model_validator(mode="after")
    def _receipt_binds_execution(self) -> ModelGoalSupervisorFinalizationRequest:
        execution = self.execution
        receipt = execution.execution_receipt
        manifest = execution.request.policy.subject_manifest
        if manifest is None:
            raise ValueError("protected subject manifest is required")
        if (
            receipt.result_sha256 != execution.result.content_sha256()
            or receipt.execution_request_sha256
            != execution.request.execution_plan_sha256()
            or receipt.policy_sha256 != execution.request.policy.content_sha256()
            or receipt.execution_identity != execution.execution_identity
            or receipt.issuer_domain != execution.request.policy.issuer_domain
            or receipt.execution_record_id != execution.execution_record_id
            or receipt.goal_id != execution.request.attempt_snapshot.goal_id
            or receipt.repository != execution.request.attempt_snapshot.repository
            or receipt.contract_revision
            != execution.request.attempt_snapshot.contract_revision
            or receipt.contract_schema_version
            != execution.request.contract.contract_schema_version
            or receipt.contract_path != execution.request.contract.contract_path
            or receipt.contract_source_commit_sha
            != execution.request.contract.contract_source_commit_sha
            or receipt.contract_sha256 != execution.request.contract.contract_sha256
            or receipt.subject_commit_sha
            != execution.request.attempt_snapshot.subject_commit_sha
            or receipt.subject_tree_sha
            != execution.request.attempt_snapshot.subject_tree_sha
            or receipt.attempt_id != execution.request.attempt_id
            or receipt.attempt_sequence != execution.request.attempt_sequence
            or receipt.running_attempt_store_revision
            != execution.request.attempt_snapshot.store_revision
            or receipt.running_attempt_snapshot_sha256
            != execution.request.attempt_snapshot.snapshot_sha256
            or receipt.verifier_artifact_sha256
            != execution.request.policy.verifier_artifact_sha256
            or receipt.policy_revision != execution.request.policy.policy_revision
            or receipt.evaluation_observation_sha256
            != execution.request.evaluation_observation.content_sha256()
            or receipt.subject_manifest_sha256 != manifest.content_sha256()
            or receipt.started_at != execution.started_at
            or receipt.completed_at != execution.completed_at
            or tuple(sorted(receipt.artifact_sha256))
            != execution.result.artifact_sha256
        ):
            raise ValueError("detached receipt does not bind the execution result")
        return self
