# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, contract-owned pins for cross-repository goal evidence."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_goal_subject_kind import EnumGoalSubjectKind

if TYPE_CHECKING:
    from omnibase_core.models.validation.model_goal_evaluation_observation import (
        ModelGoalEvaluationObservation,
    )
    from omnibase_core.models.validation.model_goal_supervisor_attestation import (
        ModelGoalSupervisorAttestation,
    )
    from omnibase_core.models.validation.model_goal_supervisor_execution_receipt import (
        ModelGoalSupervisorExecutionReceipt,
    )


from omnibase_core.constants.constants_goal_admission import (
    _REPOSITORY_RE,
    is_canonical_git_head_ref,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_goal_dependency_proof_pin import (
    ModelGoalDependencyProofPin,
)
from omnibase_core.models.validation.model_goal_execution_result import (
    ModelGoalExecutionResult,
)


class ModelGoalSubjectManifest(BaseModel):
    """Contract-owned exact dependency pins and explicit parent seam proof.

    The enclosing contract's existing canonical digest binds this manifest. The
    manifest intentionally omits owner/revision/subject authority fields: those
    remain sourced from the contract and signed supervisor attestation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    phase: Literal["pre_merge", "post_merge", "deployment"]
    required_subject_kind: EnumGoalSubjectKind
    commit_source: Literal["pull_request", "branch"] | None = None
    subject_ref: str | None = None
    base_ref: str | None = None
    dependencies: tuple[ModelGoalDependencyProofPin, ...] = Field(default_factory=tuple)
    parent_integration_criterion_id: str | None = (
        Field(  # string-id-ok: protected criterion key
            default=None, min_length=1, max_length=128
        )
    )

    @model_validator(mode="after")
    def _manifest_names_unique_dependencies(self) -> Self:
        phase_subject_kind: dict[str, EnumGoalSubjectKind] = {
            "pre_merge": EnumGoalSubjectKind.MERGE_GROUP,
            "post_merge": EnumGoalSubjectKind.COMMIT,
            "deployment": EnumGoalSubjectKind.DEPLOYMENT,
        }
        if self.required_subject_kind != phase_subject_kind[self.phase]:
            raise ValueError("manifest phase must require its canonical subject kind")
        if self.required_subject_kind == EnumGoalSubjectKind.COMMIT:
            if self.commit_source is None or self.subject_ref is None:
                raise ValueError(
                    "commit manifests require commit_source and exact subject_ref"
                )
            if not is_canonical_git_head_ref(self.subject_ref):
                raise ValueError("subject_ref must be a fully qualified Git head ref")
            if self.commit_source == "pull_request":
                if self.base_ref is None or not is_canonical_git_head_ref(
                    self.base_ref
                ):
                    raise ValueError(
                        "pull-request manifests require an exact fully qualified base_ref"
                    )
            elif self.base_ref is not None:
                raise ValueError(
                    "branch manifests cannot declare a pull-request base_ref"
                )
        elif any(
            value is not None
            for value in (self.commit_source, self.subject_ref, self.base_ref)
        ):
            raise ValueError(
                "merge-group and deployment manifests cannot declare commit source fields"
            )
        names = [pin.dependency_id for pin in self.dependencies]
        if len(set(names)) != len(names):
            raise ValueError("dependency ids must be unique")
        if self.dependencies and self.parent_integration_criterion_id is None:
            raise ValueError(
                "cross-repository dependencies require a protected parent integration criterion"
            )
        return self

    def validate_observation_subject(
        self, observation: ModelGoalEvaluationObservation
    ) -> None:
        """Require the trusted observation to match the sealed subject kind."""
        if observation.subject_kind != self.required_subject_kind:
            raise ModelOnexError(
                "recorded observation does not match manifest subject kind",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if self.required_subject_kind == EnumGoalSubjectKind.COMMIT and (
            observation.commit_source != self.commit_source
            or observation.subject_ref != self.subject_ref
            or observation.base_ref != self.base_ref
        ):
            raise ModelOnexError(
                "recorded commit source does not match the sealed subject selector",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

    def content_sha256(self) -> str:
        """Return canonical content digest; contract digest remains the authority."""
        payload = {
            "phase": self.phase,
            "required_subject_kind": self.required_subject_kind,
            "commit_source": self.commit_source,
            "subject_ref": self.subject_ref,
            "base_ref": self.base_ref,
            "dependencies": [
                pin.model_dump(mode="json")
                for pin in sorted(
                    self.dependencies, key=lambda item: item.dependency_id
                )
            ],
            "parent_integration_criterion_id": self.parent_integration_criterion_id,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"

    def validate_for_owner(self, *, repository: str, goal_id: UUID) -> None:
        """Reject dependency cycles using owner identity sourced by the caller."""
        if not _REPOSITORY_RE.fullmatch(repository):
            raise ModelOnexError(
                "owner repository must be canonical owner/repository",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        for pin in self.dependencies:
            if pin.repository != repository or pin.goal_id != goal_id:
                continue
            if pin.proof_kind in {"merge_result", "published_pass", "terminal"}:
                raise ModelOnexError(
                    "manifest cannot depend on its own merge/PASS/TERMINAL proof",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            if self.phase == "pre_merge" and pin.proof_kind == "deployment":
                raise ModelOnexError(
                    "pre-merge manifest cannot depend on its own deployment",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

    def validate_available_dependencies(
        self, available: dict[str, ModelGoalDependencyProofPin]
    ) -> None:
        """Match every declared pin exactly; ambient unrelated proofs are ignored."""
        for expected in self.dependencies:
            actual = available.get(expected.dependency_id)
            if actual != expected:
                raise ModelOnexError(
                    f"dependency {expected.dependency_id!r} is missing or differs from its contract pin",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

    def validate_parent_integration_criterion(
        self, *, protected_criterion_ids: set[str]
    ) -> None:
        """Require the sealed declaration to name a protected criterion."""
        if self.parent_integration_criterion_id is None:
            if self.dependencies:
                raise ModelOnexError(
                    "parent integration criterion is required",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            return
        if self.parent_integration_criterion_id not in protected_criterion_ids:
            raise ModelOnexError(
                "parent integration criterion must be protected",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

    def validate_parent_integration_result(
        self, result: ModelGoalExecutionResult
    ) -> None:
        """Require produced R to contain a passing parent seam record."""
        criterion_id = self.parent_integration_criterion_id
        if criterion_id is None:
            if self.dependencies:
                raise ModelOnexError(
                    "parent integration criterion is required",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            return
        evidence_by_id = {item.criterion_id: item for item in result.criterion_evidence}
        evidence = evidence_by_id.get(criterion_id)
        raw_parent_checks = [
            item
            for item in result.raw_check_outcomes
            if item.criterion_id == criterion_id
        ]
        if (
            evidence is None
            or evidence.outcome != "passed"
            or not raw_parent_checks
            or any(item.outcome != "passed" for item in raw_parent_checks)
        ):
            raise ModelOnexError(
                "execution result R must independently pass the parent integration criterion",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

    def validate_produced_evidence(
        self,
        *,
        result: ModelGoalExecutionResult,
        receipt: ModelGoalSupervisorExecutionReceipt,
        attestation: ModelGoalSupervisorAttestation,
        observation: ModelGoalEvaluationObservation,
    ) -> None:
        """Validate the two-phase R -> receipt -> final-attestation binding."""
        self.validate_observation_subject(observation)
        self.validate_parent_integration_result(result)
        if (
            receipt.attempt_id != result.attempt_id
            or receipt.repository != observation.repository
            or receipt.goal_id != observation.goal_id
            or receipt.contract_revision != observation.contract_revision
            or receipt.subject_commit_sha != observation.subject_commit_sha
            or receipt.subject_tree_sha != observation.subject_tree_sha
            or receipt.subject_manifest_sha256 != self.content_sha256()
            or receipt.result_sha256 != result.content_sha256()
            or receipt.artifact_sha256 != result.artifact_sha256
            or receipt.evaluation_observation_sha256 != observation.content_sha256()
            or not receipt.signature
        ):
            raise ModelOnexError(
                "trusted execution receipt does not bind subject, manifest, or result R",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if (
            receipt.started_at < observation.observed_at
            or receipt.started_at > observation.deadline_at
            or receipt.completed_at > observation.deadline_at
        ):
            raise ModelOnexError(
                "execution receipt must complete within the trusted observation deadline",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if (
            attestation.execution_record_id != receipt.execution_record_id
            or attestation.attempt_id != result.attempt_id
            or attestation.attempt_result_sha256 != result.content_sha256()
            or attestation.attempt_artifact_sha256 != result.artifact_sha256
            or attestation.execution_receipt_sha256 != receipt.content_sha256()
            or attestation.repository != receipt.repository
            or attestation.goal_id != receipt.goal_id
            or attestation.contract_revision != receipt.contract_revision
            or attestation.subject_commit_sha != receipt.subject_commit_sha
            or attestation.subject_tree_sha != receipt.subject_tree_sha
            or attestation.issuer_domain != receipt.issuer_domain
            or attestation.execution_identity != receipt.execution_identity
            or attestation.verifier_artifact_sha256 != receipt.verifier_artifact_sha256
            or attestation.policy_revision != receipt.policy_revision
            or not attestation.binds_evaluation_observation(observation)
        ):
            raise ModelOnexError(
                "final supervisor attestation must bind R, its artifacts, and trusted receipt",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

    def validate_no_self_reference(
        self,
        *,
        repository: str,
        goal_id: UUID,
        final_attestation: ModelGoalSupervisorAttestation,
    ) -> None:
        """Refuse a manifest pin that names this evaluation's final output."""
        final_digest = final_attestation.content_sha256()
        for pin in self.dependencies:
            if pin.repository != repository or pin.goal_id != goal_id:
                continue
            if (
                pin.attestation_id == final_attestation.attestation_id
                or pin.signed_attestation_sha256 == final_digest
            ):
                raise ModelOnexError(
                    "contract manifest cannot pin its own future final attestation",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
