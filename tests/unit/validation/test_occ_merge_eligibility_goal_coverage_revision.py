# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protected criterion coverage and append-only goal revision controls."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.crypto.crypto_ed25519_signer import generate_keypair, sign_base64
from omnibase_core.enums.enum_goal_attempt_status import EnumGoalAttemptStatus
from omnibase_core.enums.enum_occ_eligibility_reason import EnumOccEligibilityReason
from omnibase_core.enums.enum_work_outcome import EnumWorkOutcome
from omnibase_core.enums.ticket.enum_dod_check_type import EnumDodCheckType
from omnibase_core.models.contracts.ticket.model_dod_evidence_item import (
    ModelDodEvidenceItem,
)
from omnibase_core.models.envelope.model_message_envelope import ModelMessageEnvelope
from omnibase_core.models.events.work import (
    ModelSessionActor,
    ModelWorkClaimRequested,
    ModelWorkEvent,
    ModelWorkGoalRevised,
    ModelWorkResultRecorded,
    ModelWorkRulingRecorded,
)
from omnibase_core.models.events.work.model_work_goal_revision_resolution import (
    ModelWorkGoalRevisionResolution,
)
from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem
from omnibase_core.models.validation.model_goal_admission_observation import (
    ModelGoalAdmissionObservation,
)
from omnibase_core.models.validation.model_goal_attempt_allocation_snapshot import (
    ModelGoalAttemptAllocationSnapshot,
)
from omnibase_core.models.validation.model_goal_check_execution_outcome import (
    ModelGoalCheckExecutionOutcome,
)
from omnibase_core.models.validation.model_goal_commit_source_readback import (
    ModelGoalCommitSourceReadback,
)
from omnibase_core.models.validation.model_goal_complete_absence_proof import (
    ModelGoalCompleteAbsenceProof,
)
from omnibase_core.models.validation.model_goal_contract_revision_record import (
    ModelGoalContractRevisionRecord,
)
from omnibase_core.models.validation.model_goal_criterion_baseline import (
    ModelGoalCriterionBaseline,
)
from omnibase_core.models.validation.model_goal_criterion_execution_evidence import (
    ModelGoalCriterionExecutionEvidence,
)
from omnibase_core.models.validation.model_goal_criterion_requirement import (
    ModelGoalCriterionRequirement,
)
from omnibase_core.models.validation.model_goal_dependency_admission_evidence import (
    ModelGoalDependencyAdmissionEvidence,
)
from omnibase_core.models.validation.model_goal_dependency_issuer_binding import (
    ModelGoalDependencyIssuerBinding,
)
from omnibase_core.models.validation.model_goal_dependency_proof_pin import (
    ModelGoalDependencyProofPin,
)
from omnibase_core.models.validation.model_goal_evaluation_observation import (
    ModelGoalEvaluationObservation,
)
from omnibase_core.models.validation.model_goal_execution_result import (
    ModelGoalExecutionResult,
)
from omnibase_core.models.validation.model_goal_fork_resolution_record import (
    ModelGoalForkResolutionRecord,
)
from omnibase_core.models.validation.model_goal_merge_group_source_readback import (
    ModelGoalMergeGroupSourceReadback,
)
from omnibase_core.models.validation.model_goal_mutation_confirmation import (
    ModelGoalMutationConfirmation,
)
from omnibase_core.models.validation.model_goal_mutation_context import (
    ModelGoalMutationContext,
)
from omnibase_core.models.validation.model_goal_mutation_context_readback import (
    ModelGoalMutationContextReadback,
)
from omnibase_core.models.validation.model_goal_mutation_intent import (
    ModelGoalMutationIntent,
)
from omnibase_core.models.validation.model_goal_mutation_state import (
    ModelGoalMutationState,
)
from omnibase_core.models.validation.model_goal_protected_baseline_file import (
    ModelGoalProtectedBaselineFile,
)
from omnibase_core.models.validation.model_goal_required_check_binding import (
    ModelGoalRequiredCheckBinding,
)
from omnibase_core.models.validation.model_goal_revision_authorization_policy import (
    ModelGoalRevisionAuthorizationPolicy,
)
from omnibase_core.models.validation.model_goal_revision_history_snapshot import (
    ModelGoalRevisionHistorySnapshot,
)
from omnibase_core.models.validation.model_goal_selector_execution_outcome import (
    ModelGoalSelectorExecutionOutcome,
)
from omnibase_core.models.validation.model_goal_subject_manifest import (
    ModelGoalSubjectManifest,
)
from omnibase_core.models.validation.model_goal_supervisor_attestation import (
    ModelGoalSupervisorAttestation,
)
from omnibase_core.models.validation.model_goal_supervisor_execution_receipt import (
    ModelGoalSupervisorExecutionReceipt,
)
from omnibase_core.models.validation.model_goal_verification_attempt import (
    ModelGoalVerificationAttempt,
)
from omnibase_core.models.validation.model_goal_verifier_policy import (
    ModelGoalVerifierPolicy,
)
from omnibase_core.nodes.node_work_ledger_state_compute.handler import fold_work_events
from omnibase_core.utils.util_goal_verification import (
    compute_goal_execution_request_sha256,
    compute_goal_resolution_event_sha256,
)
from omnibase_core.validation.validator_occ_merge_eligibility import (
    _validate_goal_criterion_coverage,
    _validate_goal_revision_history,
    compute_goal_check_value_sha256,
    compute_goal_criterion_coverage_sha256,
    validate_occ_merge_eligibility,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)
from tests.unit.validation.test_occ_merge_eligibility_identity import (
    CONTRACT_REVISION,
    CONTRACT_SCHEMA_VERSION,
    GOAL_CHECK_TYPE,
    GOAL_CHECK_VALUE,
    GOAL_ID,
    GOAL_ITEM_ID,
    REPOSITORY,
    _canonical_goal_sha256,
    _goal_contract,
    _goal_repo,
)
from tests.unit.validation.test_occ_merge_eligibility_trusted_goal_admission import (
    _attempt_snapshot,
    _input,
)

if TYPE_CHECKING:
    from omnibase_core.models.validation.model_goal_attempt_allocation_snapshot import (
        ModelGoalAttemptAllocationSnapshot,
    )

CRITERION_ID = "criterion-goal-contract"
PROTECTED_TEST_PATH = "tests/test_goal_criterion_baseline.py"
_BASELINE_TEST = b"def test_goal_criterion_is_exercised():\n    assert True\n"
_OTHER_REVISION = UUID("00000000-0000-4000-8000-000000000099")
_THIRD_REVISION = UUID("00000000-0000-4000-8000-000000000100")
_FOURTH_REVISION = UUID("00000000-0000-4000-8000-000000000101")
_ISSUER_DOMAIN = "org.omninode.supervisor"
_EXECUTION_IDENTITY = "github-actions/goal-verifier"
_POLICY_REVISION = UUID("00000000-0000-4000-8000-000000000451")
_VERIFIER_BYTES = b"protected goal verifier fixture"
_OBSERVED_AT = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
_WORK_ACTOR = ModelSessionActor(session_handle="or2-revision-test", agent_kind="test")
_WORK_LEDGER_RUNTIME_ID = "runtime-or2-work-ledger"
_UNAUTHORIZED_WORK_LEDGER_RUNTIME_ID = "runtime-unapproved-work-ledger"
_WORK_LEDGER_KEYPAIR = generate_keypair()
_DEPENDENCY_ISSUER_DOMAIN = "org.omninode.dependency-release"
_APP_INTEGRATION_ID = "app-installation-or2-fixture"
_REQUIRED_CONTEXT = "Goal / OMN-20070 / required"


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _signed_external_dependency() -> tuple[
    ModelGoalDependencyProofPin,
    ModelGoalDependencyAdmissionEvidence,
    bytes,
    bytes,
]:
    repository = "OmniNode-ai/omnibase_infra"
    goal_id = _OTHER_REVISION
    revision = _THIRD_REVISION
    subject_commit = "a" * 40
    subject_tree = "b" * 40
    contract_sha256 = _sha256(b"immutable infra dependency contract")
    artifact = b"official infra dependency artifact"
    artifact_digest = _sha256(artifact)
    keypair = generate_keypair()
    verifier_digest = _sha256(b"infra pinned verifier")
    attempt_id = UUID("00000000-0000-4000-8000-000000000703")
    execution_record_id = UUID("00000000-0000-4000-8000-000000000704")
    attempt_store_revision = UUID("00000000-0000-4000-8000-000000000705")
    running_store_revision = UUID("00000000-0000-4000-8000-000000000706")
    attempt_result_sha256 = _sha256(b"infra execution result")
    running_snapshot_sha256 = _sha256(b"infra running snapshot")
    execution_request_sha256 = _sha256(b"infra execution request")
    observation = ModelGoalEvaluationObservation(
        observation_id=UUID("00000000-0000-4000-8000-000000000701"),
        deadline_event_id=UUID("00000000-0000-4000-8000-000000000702"),
        repository=repository,
        goal_id=goal_id,
        contract_revision=revision,
        subject_commit_sha=subject_commit,
        subject_tree_sha=subject_tree,
        subject_kind="commit",
        commit_source="branch",
        subject_ref="refs/heads/main",
        subject_repository=repository,
        observed_at=_OBSERVED_AT,
        deadline_at=_OBSERVED_AT + timedelta(hours=1),
    )
    manifest = ModelGoalSubjectManifest.model_validate(
        {
            "phase": "post_merge",
            "required_subject_kind": "commit",
            "commit_source": "branch",
            "subject_ref": "refs/heads/main",
            "dependencies": [],
            "parent_integration_criterion_id": None,
        }
    )
    baseline = ModelGoalCriterionBaseline(
        requirements=(
            ModelGoalCriterionRequirement(
                criterion_id="infra-criterion",
                criterion_definition="The pinned infrastructure check passed.",
                required_checks=(
                    ModelGoalRequiredCheckBinding(
                        item_id="infra-check",
                        check_type=EnumDodCheckType.COMMAND,
                        check_value_sha256=_sha256(b"uv run pytest"),
                    ),
                ),
                required_test_selectors=("tests/fixtures/infra_goal.py::test_proof",),
                negative_control_selectors=(
                    "tests/fixtures/infra_goal.py::test_proof",
                ),
                test_and_fixture_files=(
                    ModelGoalProtectedBaselineFile(
                        path="tests/fixtures/infra_goal.py",
                        sha256=_sha256(b"protected infra test"),
                    ),
                ),
            ),
        )
    )
    policy = ModelGoalVerifierPolicy(
        repository=repository,
        goal_id=goal_id,
        contract_revision=revision,
        policy_revision=_THIRD_REVISION,
        issuer_domain=_DEPENDENCY_ISSUER_DOMAIN,
        verifier_artifact_sha256=verifier_digest,
        allowed_execution_identities=("github-actions/infra-goal-verifier",),
        max_attestation_age_seconds=3600,
        criterion_baseline=baseline,
        subject_manifest=manifest,
    )
    running_attempt = ModelGoalVerificationAttempt(
        goal_id=goal_id,
        repository=repository,
        contract_revision=revision,
        subject_commit_sha=subject_commit,
        subject_tree_sha=subject_tree,
        attempt_id=attempt_id,
        sequence=1,
        status=EnumGoalAttemptStatus.PASS,
        execution_request_sha256=execution_request_sha256,
        running_store_revision=running_store_revision,
        running_snapshot_sha256=running_snapshot_sha256,
        result_sha256=attempt_result_sha256,
        artifact_sha256=(artifact_digest,),
    )
    attempt_values: dict[str, Any] = {
        "goal_id": goal_id,
        "repository": repository,
        "contract_revision": revision,
        "subject_commit_sha": subject_commit,
        "subject_tree_sha": subject_tree,
        "allocation_count": 1,
        "watermark_sequence": 1,
        "store_revision": attempt_store_revision,
        "attempts": (running_attempt,),
    }
    attempts = ModelGoalAttemptAllocationSnapshot(
        **attempt_values,
        snapshot_sha256=ModelGoalAttemptAllocationSnapshot.compute_snapshot_sha256(
            **attempt_values
        ),
    )
    history_sha256 = _sha256(b"infra revision history")
    coverage_sha256 = _sha256(b"infra criterion coverage")
    execution_values: dict[str, Any] = {
        "execution_record_id": execution_record_id,
        "issuer_domain": _DEPENDENCY_ISSUER_DOMAIN,
        "goal_id": goal_id,
        "repository": repository,
        "contract_revision": revision,
        "contract_schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_path": "contracts/goals/infra.yaml",
        "contract_source_commit_sha": "c" * 40,
        "contract_sha256": contract_sha256,
        "subject_commit_sha": subject_commit,
        "subject_tree_sha": subject_tree,
        "attempt_id": attempt_id,
        "attempt_sequence": 1,
        "running_attempt_store_revision": running_store_revision,
        "running_attempt_snapshot_sha256": running_snapshot_sha256,
        "execution_request_sha256": execution_request_sha256,
        "result_sha256": attempt_result_sha256,
        "artifact_sha256": (artifact_digest,),
        "subject_manifest_sha256": manifest.content_sha256(),
        "evaluation_observation_sha256": observation.content_sha256(),
        "verifier_artifact_sha256": verifier_digest,
        "policy_revision": policy.policy_revision,
        "execution_identity": "github-actions/infra-goal-verifier",
        "started_at": _OBSERVED_AT + timedelta(seconds=1),
        "completed_at": _OBSERVED_AT + timedelta(seconds=2),
        "signature": "pending-signature",
    }
    execution_receipt = ModelGoalSupervisorExecutionReceipt.model_validate(
        execution_values
    )
    execution_receipt = execution_receipt.model_copy(
        update={
            "signature": sign_base64(
                keypair.private_key_bytes, execution_receipt.signing_payload()
            )
        }
    )
    attestation_values: dict[str, Any] = {
        "attestation_id": _FOURTH_REVISION,
        "issuer_domain": _DEPENDENCY_ISSUER_DOMAIN,
        "goal_id": goal_id,
        "repository": repository,
        "contract_revision": revision,
        "contract_schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_path": "contracts/goals/infra.yaml",
        "contract_source_commit_sha": "c" * 40,
        "contract_sha256": contract_sha256,
        "subject_commit_sha": subject_commit,
        "subject_tree_sha": subject_tree,
        "attempt_id": attempt_id,
        "attempt_sequence": 1,
        "execution_record_id": execution_record_id,
        "execution_receipt_sha256": execution_receipt.content_sha256(),
        "attempt_result_sha256": attempt_result_sha256,
        "attempt_artifact_sha256": (artifact_digest,),
        "subject_manifest_sha256": manifest.content_sha256(),
        "evaluation_observation_sha256": observation.content_sha256(),
        "attempt_store_revision": attempts.store_revision,
        "attempt_snapshot_sha256": attempts.snapshot_sha256,
        "criterion_baseline_sha256": baseline.content_sha256(),
        "criterion_coverage_sha256": coverage_sha256,
        "revision_history_sha256": history_sha256,
        "evaluation_observation_id": observation.observation_id,
        "deadline_event_id": observation.deadline_event_id,
        "verifier_artifact_sha256": verifier_digest,
        "policy_revision": policy.policy_revision,
        "execution_identity": "github-actions/infra-goal-verifier",
        "issued_at": _OBSERVED_AT + timedelta(seconds=3),
        "expires_at": _OBSERVED_AT + timedelta(minutes=30),
        "signature": "pending-signature",
    }
    attestation = ModelGoalSupervisorAttestation.model_validate(attestation_values)
    attestation = attestation.model_copy(
        update={
            "signature": sign_base64(
                keypair.private_key_bytes, attestation.signing_payload()
            )
        }
    )
    admission_observation = ModelGoalAdmissionObservation(
        observation_id=UUID("00000000-0000-4000-8000-000000000708"),
        repository=repository,
        goal_id=goal_id,
        contract_revision=revision,
        subject_commit_sha=subject_commit,
        subject_tree_sha=subject_tree,
        attempt_id=attempt_id,
        attempt_sequence=1,
        attempt_store_revision=attempts.store_revision,
        attempt_snapshot_sha256=attempts.snapshot_sha256,
        contract_sha256=contract_sha256,
        execution_record_id=execution_receipt.execution_record_id,
        execution_receipt_sha256=execution_receipt.content_sha256(),
        attestation_id=attestation.attestation_id,
        attestation_sha256=attestation.content_sha256(),
        policy_revision=policy.policy_revision,
        policy_sha256=policy.content_sha256(),
        verifier_artifact_sha256=policy.verifier_artifact_sha256,
        criterion_baseline_sha256=baseline.content_sha256(),
        criterion_coverage_sha256=coverage_sha256,
        revision_history_sha256=history_sha256,
        evaluation_observation_id=observation.observation_id,
        evaluation_observation_sha256=observation.content_sha256(),
        deadline_event_id=observation.deadline_event_id,
        deadline_at=observation.deadline_at,
        observed_at=_OBSERVED_AT + timedelta(seconds=4),
    )
    pin = ModelGoalDependencyProofPin(
        dependency_id="infra-published-core",
        proof_kind="commit_check",
        repository=repository,
        goal_id=goal_id,
        contract_revision=revision,
        contract_sha256=contract_sha256,
        subject_kind="commit",
        subject_commit_sha=subject_commit,
        subject_tree_sha=subject_tree,
        attestation_id=attestation.attestation_id,
        signed_attestation_sha256=attestation.content_sha256(),
        artifact_sha256=(artifact_digest,),
    )
    evidence = ModelGoalDependencyAdmissionEvidence(
        attempts=attempts,
        policy=policy,
        initial_observation=observation,
        execution_receipt=execution_receipt,
        attestation=attestation,
        admission_observation=admission_observation,
    )
    return pin, evidence, keypair.public_key_bytes, artifact


def _git(repo_root: Path, *args: str) -> str:
    import subprocess

    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
        env=scrub_git_location_env(),
    )
    return result.stdout.strip()


def _coverage_fixture(
    tmp_path: Path,
    *,
    check_type: str = GOAL_CHECK_TYPE,
    binds_ac: tuple[str, ...] | None = (CRITERION_ID,),
    subject_manifest: dict[str, Any] | None = None,
    second_item: bool = False,
) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    contract = _goal_contract(second_item=second_item)
    if subject_manifest is not None:
        contract["subject_manifest"] = subject_manifest
    evidence = contract["dod_evidence"]
    assert isinstance(evidence, list) and isinstance(evidence[0], dict)
    evidence[0]["checks"][0]["check_type"] = check_type
    if binds_ac is not None:
        evidence[0]["binds_ac"] = list(binds_ac)
    else:
        evidence[0].pop("binds_ac", None)
    fixture = _goal_repo(tmp_path, contract=contract)
    repo_root = fixture["repo_root"]
    assert isinstance(repo_root, Path)
    path = repo_root / PROTECTED_TEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_BASELINE_TEST)
    _git(repo_root, "add", PROTECTED_TEST_PATH)
    _git(repo_root, "commit", "-m", "add protected criterion test")
    fixture["subject_commit"] = _git(repo_root, "rev-parse", "HEAD")
    fixture["subject_tree"] = _git(repo_root, "rev-parse", "HEAD^{tree}")
    fixture["contract"] = contract
    return fixture


def _requirement(
    fixture: dict[str, Any],
    *,
    item_id: str = GOAL_ITEM_ID,
    check_type: str = GOAL_CHECK_TYPE,
    check_value: Any = GOAL_CHECK_VALUE,
    file_path: str = PROTECTED_TEST_PATH,
    file_bytes: bytes = _BASELINE_TEST,
) -> ModelGoalCriterionRequirement:
    return ModelGoalCriterionRequirement(
        criterion_id=CRITERION_ID,
        criterion_definition="The protected goal criterion is satisfied.",
        required_checks=(
            ModelGoalRequiredCheckBinding(
                item_id=item_id,
                check_type=EnumDodCheckType(check_type),
                check_value_sha256=compute_goal_check_value_sha256(check_value),
            ),
        ),
        required_test_selectors=(f"{file_path}::test_goal_criterion_is_exercised",),
        negative_control_selectors=(f"{file_path}::test_goal_criterion_is_exercised",),
        test_and_fixture_files=(
            ModelGoalProtectedBaselineFile(
                path=file_path,
                sha256=_sha256(file_bytes),
            ),
        ),
    )


def _evidence_items(contract: dict[str, Any]) -> tuple[ModelDodEvidenceItem, ...]:
    return tuple(
        ModelDodEvidenceItem.model_validate(raw) for raw in contract["dod_evidence"]
    )


def _coverage(
    fixture: dict[str, Any],
    baseline: ModelGoalCriterionBaseline,
    *,
    evidence_items: tuple[ModelDodEvidenceItem, ...] | None = None,
):
    repo_root = fixture["repo_root"]
    assert isinstance(repo_root, Path)
    return _validate_goal_criterion_coverage(
        root=repo_root,
        subject_commit_sha=str(fixture["subject_commit"]),
        evidence_items=evidence_items or _evidence_items(fixture["contract"]),
        policy=type("PolicyFixture", (), {"criterion_baseline": baseline})(),
    )


def _revision(
    revision_id: UUID,
    fixture: dict[str, Any],
    *,
    parent: UUID | None,
    contract_sha256: str | None = None,
) -> ModelGoalContractRevisionRecord:
    contract = fixture["contract"]
    assert isinstance(contract, dict)
    items = tuple(
        ModelContractDodItem.model_validate(item) for item in contract["dod_evidence"]
    )
    common = {
        "event_id": revision_id,
        "emitted_at": _OBSERVED_AT,
        "actor": _WORK_ACTOR,
        "ticket_id": "OMN-20070",
        "summary": "bind a complete immutable goal contract revision",
        "goal_id": GOAL_ID,
        "repository": REPOSITORY,
        "contract_source_commit_sha": str(fixture["contract_source_commit"]),
        "contract_path": "contracts/goals/example.yaml",
        "contract_sha256": contract_sha256 or _canonical_goal_sha256(contract),
        "contract_schema_version": CONTRACT_SCHEMA_VERSION,
        "dod_evidence": items,
        "authorization_policy_revision": _POLICY_REVISION,
    }
    if parent is None:
        source_event = ModelWorkClaimRequested.model_validate(
            {**common, "goal_id": revision_id}
        )
    else:
        source_event = ModelWorkGoalRevised.model_validate(
            {
                **common,
                "replaces": parent,
                "reason": "append a complete replacement contract",
            }
        )
    source_envelope = ModelMessageEnvelope[ModelWorkEvent].create_signed(
        realm="dev",
        runtime_id=_WORK_LEDGER_RUNTIME_ID,
        bus_id="or2-work-ledger-source-test",
        payload=source_event,
        private_key=_WORK_LEDGER_KEYPAIR.private_key_bytes,
        emitted_at=source_event.emitted_at,
    )
    return ModelGoalContractRevisionRecord(
        goal_id=GOAL_ID,
        revision_id=revision_id,
        replaces_revision_id=parent,
        repository=REPOSITORY,
        contract_schema_version=CONTRACT_SCHEMA_VERSION,
        contract_path="contracts/goals/example.yaml",
        contract_source_commit_sha=str(fixture["contract_source_commit"]),
        contract_sha256=contract_sha256 or _canonical_goal_sha256(contract),
        dod_evidence=items,
        authorization_policy_revision=_POLICY_REVISION,
        source_event=source_event,
        source_envelope=source_envelope,
    )


def _revision_history(
    fixture: dict[str, Any],
    revisions: tuple[ModelGoalContractRevisionRecord, ...],
    resolutions: tuple[ModelGoalForkResolutionRecord, ...] = (),
    *,
    allowed_actor_keys: tuple[str, ...] = (_WORK_ACTOR.actor_key,),
    allowed_event_runtime_ids: tuple[str, ...] = (_WORK_LEDGER_RUNTIME_ID,),
) -> ModelGoalRevisionHistorySnapshot:
    policy_payload = {
        "repository": REPOSITORY,
        "goal_id": str(GOAL_ID),
        "policy_revision": str(_POLICY_REVISION),
        "allowed_actor_keys": sorted(allowed_actor_keys),
        "allowed_event_runtime_ids": sorted(allowed_event_runtime_ids),
    }
    policy_canonical = json.dumps(policy_payload, sort_keys=True, separators=(",", ":"))
    policy_digest = _sha256(policy_canonical.encode("utf-8"))
    policies = (
        ModelGoalRevisionAuthorizationPolicy(
            repository=REPOSITORY,
            goal_id=GOAL_ID,
            policy_revision=_POLICY_REVISION,
            allowed_actor_keys=allowed_actor_keys,
            allowed_event_runtime_ids=allowed_event_runtime_ids,
            policy_sha256=policy_digest,
        ),
    )
    history = ModelGoalRevisionHistorySnapshot(
        repository=REPOSITORY,
        goal_id=GOAL_ID,
        store_revision=uuid4(),
        revisions=revisions,
        fork_resolutions=resolutions,
        revision_authorization_policies=policies,
        snapshot_sha256=_sha256(b"placeholder"),
    )
    return history.model_copy(update={"snapshot_sha256": history.content_sha256()})


def _fork_resolution(
    *,
    children: tuple[UUID, ...],
    selected: UUID,
    parent: UUID = GOAL_ID,
    goal_id: UUID = GOAL_ID,
    authorization_sha256: str | None = None,
    policy_revision: UUID = _POLICY_REVISION,
    actor: ModelSessionActor = _WORK_ACTOR,
    runtime_id: str = _WORK_LEDGER_RUNTIME_ID,
) -> ModelGoalForkResolutionRecord:
    event_id = uuid4()
    event = ModelWorkRulingRecorded(
        event_id=event_id,
        emitted_at=_OBSERVED_AT,
        actor=actor,
        ticket_id="OMN-20070",
        summary="structured fork resolution fixture",
        operator_words="Select the requested branch.",
        goal_revision_resolution=ModelWorkGoalRevisionResolution(
            goal_id=goal_id,
            repository=REPOSITORY,
            fork_parent_revision_id=parent,
            competing_revision_ids=children,
            selected_revision_id=selected,
            resolution_policy_revision=policy_revision,
        ),
    )
    envelope = ModelMessageEnvelope[ModelWorkRulingRecorded].create_signed(
        realm="dev",
        runtime_id=runtime_id,
        bus_id="or2-work-ledger-test",
        payload=event,
        private_key=_WORK_LEDGER_KEYPAIR.private_key_bytes,
        emitted_at=event.emitted_at,
    )
    return ModelGoalForkResolutionRecord(
        goal_id=goal_id,
        repository=REPOSITORY,
        fork_parent_revision_id=parent,
        competing_revision_ids=children,
        selected_revision_id=selected,
        resolution_policy_revision=policy_revision,
        authorization_event_id=event_id,
        authorization_sha256=authorization_sha256
        or compute_goal_resolution_event_sha256(event),
        authorization_event=event,
        authorization_envelope=envelope,
    )


@dataclass(frozen=True)
class _WorkLedgerKeyProvider:
    """Small test keyring used by the native signed Work Ledger envelope."""

    public_keys: dict[str, bytes]

    def get_public_key(self, runtime_id: str) -> bytes | None:
        return self.public_keys.get(runtime_id)


@dataclass
class _FullProvider:
    """Test-only trusted provider for the public resolver path."""

    attempts: ModelGoalAttemptAllocationSnapshot
    policy: ModelGoalVerifierPolicy
    attestation: ModelGoalSupervisorAttestation
    execution_receipt: ModelGoalSupervisorExecutionReceipt | None
    admission_observation: ModelGoalAdmissionObservation | None
    history: ModelGoalRevisionHistorySnapshot
    observation: ModelGoalEvaluationObservation
    current_commit_source: ModelGoalCommitSourceReadback | None
    current_merge_group_source: ModelGoalMergeGroupSourceReadback | None
    trust_root: bytes
    artifacts: dict[str, bytes]
    ledger_key_provider: _WorkLedgerKeyProvider
    mutation_state: ModelGoalMutationState | None
    dependency_evidence: ModelGoalDependencyAdmissionEvidence | None = None
    dependency_trust_root: bytes | None = None

    def read_current_attempt_snapshot(self, **_: Any):
        return self.attempts

    def get_policy(self, **_: Any):
        return self.policy

    def read_current_revision_history(self, **_: Any):
        return self.history

    def get_evaluation_observation(self, **_: Any):
        return self.observation

    def read_current_commit_source(self, **_: Any):
        return self.current_commit_source

    def read_current_merge_group_source(self, **_: Any):
        return self.current_merge_group_source

    def get_attestation(self, **_: Any):
        return self.attestation

    def get_execution_receipt(self, **_: Any):
        return self.execution_receipt

    def read_current_admission_observation(self, **_: Any):
        return self.admission_observation

    def get_dependency_evidence(self, **_: Any):
        return self.dependency_evidence

    def read_current_goal_mutation_state(self, **_: Any):
        return self.mutation_state

    def get_domain_trust_root(self, domain_id: str):
        if domain_id == _ISSUER_DOMAIN:
            return self.trust_root
        if domain_id == _DEPENDENCY_ISSUER_DOMAIN:
            return self.dependency_trust_root
        raise AssertionError(f"unexpected trust domain: {domain_id}")

    def get_work_ledger_key_provider(self):
        return self.ledger_key_provider

    def read_artifact_bytes(self, digest: str):
        return self.artifacts.get(digest)


def _merge_group_observation_fields(fixture: dict[str, Any]) -> dict[str, Any]:
    merge_group_ref = f"gh-readonly-queue/main/pr-123-{fixture['subject_commit']}"
    return {
        "merge_group_id": merge_group_ref,
        "merge_group_delivery_id": UUID("00000000-0000-4000-8000-000000000321"),
        "merge_group_ref": merge_group_ref,
        "merge_group_base_ref": "main",
        "merge_group_head_ref": merge_group_ref,
        "merge_group_base_sha": str(fixture["base_commit"]),
        "merge_group_base_tree_sha": "d" * 40,
        "merge_group_head_sha": str(fixture["subject_commit"]),
        "merge_group_head_tree_sha": str(fixture["subject_tree"]),
        "merge_group_source_checkpoint_id": "topic:7:123",
        "merge_group_source_body_sha256": _sha256(b"retained group event").removeprefix(
            "sha256:"
        ),
        "merge_group_received_at": _OBSERVED_AT - timedelta(seconds=1),
    }


def _full_provider(
    fixture: dict[str, Any],
    *,
    baseline: ModelGoalCriterionBaseline | None = None,
    history: ModelGoalRevisionHistorySnapshot | None = None,
    observation: ModelGoalEvaluationObservation | None = None,
    current_commit_source: ModelGoalCommitSourceReadback | None = None,
    current_merge_group_source: ModelGoalMergeGroupSourceReadback | None = None,
    statuses: tuple[EnumGoalAttemptStatus, ...] = (EnumGoalAttemptStatus.PASS,),
    attempts_override: ModelGoalAttemptAllocationSnapshot | None = None,
    policy_override: dict[str, Any] | None = None,
    attestation_override: dict[str, Any] | None = None,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    verifier_artifact_bytes: bytes = _VERIFIER_BYTES,
    mutation_state: ModelGoalMutationState | None = None,
    failed_criterion_ids: frozenset[str] = frozenset(),
    omit_check_keys: frozenset[tuple[str, str, str]] = frozenset(),
) -> _FullProvider:
    """Create real signed trust fixtures for end-to-end resolver tests."""
    if baseline is None:
        protected_requirements = [_requirement(fixture)]
        if any(
            item.get("id") == "goal-contract-second-required-criterion"
            for item in fixture["contract"]["dod_evidence"]
        ):
            protected_requirements.append(
                ModelGoalCriterionRequirement(
                    criterion_id="criterion-second-required",
                    criterion_definition="A second required criterion is covered.",
                    required_checks=(
                        ModelGoalRequiredCheckBinding(
                            item_id="goal-contract-second-required-criterion",
                            check_type=EnumDodCheckType.COMMAND,
                            check_value_sha256=compute_goal_check_value_sha256(
                                "uv run true"
                            ),
                        ),
                    ),
                    required_test_selectors=(
                        f"{PROTECTED_TEST_PATH}::test_goal_criterion_is_exercised",
                    ),
                    negative_control_selectors=(
                        f"{PROTECTED_TEST_PATH}::test_goal_criterion_is_exercised",
                    ),
                    test_and_fixture_files=(
                        ModelGoalProtectedBaselineFile(
                            path=PROTECTED_TEST_PATH,
                            sha256=_sha256(_BASELINE_TEST),
                        ),
                    ),
                )
            )
        selected_baseline = ModelGoalCriterionBaseline(
            requirements=tuple(protected_requirements)
        )
    else:
        selected_baseline = baseline
    selected_history = history or _revision_history(
        fixture,
        (
            _revision(GOAL_ID, fixture, parent=None),
            _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID),
        ),
    )
    manifest = ModelGoalSubjectManifest.model_validate(
        fixture["contract"]["subject_manifest"]
    )
    observation_values: dict[str, Any] = {
        "observation_id": UUID("00000000-0000-4000-8000-000000000301"),
        "deadline_event_id": UUID("00000000-0000-4000-8000-000000000302"),
        "repository": REPOSITORY,
        "goal_id": GOAL_ID,
        "contract_revision": CONTRACT_REVISION,
        "subject_commit_sha": str(fixture["subject_commit"]),
        "subject_tree_sha": str(fixture["subject_tree"]),
        "subject_kind": manifest.required_subject_kind,
        "observed_at": _OBSERVED_AT,
        "deadline_at": _OBSERVED_AT + timedelta(hours=1),
        "deadline_status": "open",
        "deadline_recorded_at": None,
    }
    if manifest.required_subject_kind.value == "merge_group":
        observation_values.update(_merge_group_observation_fields(fixture))
    elif manifest.required_subject_kind.value == "commit":
        observation_values.update(
            {
                "commit_source": manifest.commit_source,
                "subject_ref": manifest.subject_ref,
                "subject_repository": REPOSITORY,
                "pull_request_number": 123
                if manifest.commit_source == "pull_request"
                else None,
                "base_repository": REPOSITORY
                if manifest.commit_source == "pull_request"
                else None,
                "base_ref": manifest.base_ref,
            }
        )
    elif manifest.required_subject_kind.value == "deployment":
        observation_values.update(
            {
                "deployment_id": "deployment-42",
                "environment_id": "production",
                "runtime_instance_id": "runtime-prod-7",
                "artifact_sha256": _sha256(b"deployed image digest"),
                "runtime_config_sha256": _sha256(b"runtime config digest"),
            }
        )
    selected_observation = observation or ModelGoalEvaluationObservation(
        **observation_values,
    )
    verifier_digest = _sha256(_VERIFIER_BYTES)
    policy_values: dict[str, Any] = {
        "repository": REPOSITORY,
        "goal_id": GOAL_ID,
        "contract_revision": CONTRACT_REVISION,
        "policy_revision": _POLICY_REVISION,
        "issuer_domain": _ISSUER_DOMAIN,
        "verifier_artifact_sha256": verifier_digest,
        "allowed_execution_identities": (_EXECUTION_IDENTITY,),
        "max_attestation_age_seconds": 3600,
        "criterion_baseline": selected_baseline,
        "subject_manifest": manifest,
    }
    if policy_override:
        policy_values.update(policy_override)
    policy = ModelGoalVerifierPolicy.model_validate(policy_values)
    coverage_digest = compute_goal_criterion_coverage_sha256(
        evidence_items=_evidence_items(fixture["contract"]),
        baseline=selected_baseline,
        protected_file_sha256={PROTECTED_TEST_PATH: _sha256(_BASELINE_TEST)},
    )
    keypair = generate_keypair()
    execution_receipt: ModelGoalSupervisorExecutionReceipt | None = None
    execution_result: ModelGoalExecutionResult | None = None
    execution_result_bytes: bytes | None = None
    if (
        attempts_override is None
        and statuses
        and statuses[-1] is EnumGoalAttemptStatus.PASS
    ):
        sequence = len(statuses)
        attempt_id = UUID(int=sequence)
        evidence_digest = _sha256(b"protected goal execution evidence")
        artifact_bytes = b"protected goal execution artifact"
        artifact_digest = _sha256(artifact_bytes)
        requirements = sorted(
            selected_baseline.requirements, key=lambda item: item.criterion_id
        )
        result = ModelGoalExecutionResult(
            attempt_id=attempt_id,
            criterion_evidence=tuple(
                ModelGoalCriterionExecutionEvidence(
                    criterion_id=requirement.criterion_id,
                    outcome=(
                        "failed"
                        if requirement.criterion_id in failed_criterion_ids
                        else "passed"
                    ),
                    evidence_sha256=evidence_digest,
                )
                for requirement in requirements
            ),
            raw_check_outcomes=tuple(
                ModelGoalCheckExecutionOutcome(
                    criterion_id=requirement.criterion_id,
                    item_id=check.item_id,
                    check_type=check.check_type,
                    check_value_sha256=check.check_value_sha256,
                    outcome=(
                        "failed"
                        if requirement.criterion_id in failed_criterion_ids
                        else "passed"
                    ),
                    evidence_sha256=evidence_digest,
                )
                for requirement in requirements
                for check in sorted(
                    requirement.required_checks,
                    key=lambda item: (item.item_id, item.check_type.value),
                )
                if (
                    requirement.criterion_id,
                    check.item_id,
                    check.check_type.value,
                )
                not in omit_check_keys
            ),
            selector_outcomes=tuple(
                ModelGoalSelectorExecutionOutcome(selector=selector, outcome="passed")
                for selector in sorted(
                    {
                        selector
                        for requirement in requirements
                        for selector in requirement.required_test_selectors
                    }
                )
            ),
            artifact_sha256=(artifact_digest,),
        )
        execution_result = result
        execution_result_bytes = json.dumps(
            result.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        result_digest = result.content_sha256()
        assert _sha256(execution_result_bytes) == result_digest
        sequence_request_sha256 = compute_goal_execution_request_sha256(
            repository=REPOSITORY,
            goal_id=GOAL_ID,
            contract_revision=CONTRACT_REVISION,
            contract_sha256=_canonical_goal_sha256(fixture["contract"]),
            policy_revision=policy.policy_revision,
            verifier_artifact_sha256=verifier_digest,
            criterion_baseline_sha256=selected_baseline.content_sha256(),
            revision_history_sha256=selected_history.snapshot_sha256,
            evaluation_observation_sha256=selected_observation.content_sha256(),
            subject_manifest_sha256=manifest.content_sha256(),
            attempt_id=attempt_id,
            attempt_sequence=sequence,
            subject_kind=manifest.required_subject_kind,
            subject_commit_sha=str(fixture["subject_commit"]),
            subject_tree_sha=str(fixture["subject_tree"]),
        )
        prior_attempts = tuple(
            ModelGoalVerificationAttempt(
                goal_id=GOAL_ID,
                repository=REPOSITORY,
                contract_revision=CONTRACT_REVISION,
                subject_commit_sha=str(fixture["subject_commit"]),
                subject_tree_sha=str(fixture["subject_tree"]),
                attempt_id=UUID(int=prior_sequence),
                sequence=prior_sequence,
                status=prior_status,
                execution_request_sha256=_sha256(
                    f"prior-request-{prior_sequence}".encode()
                ),
                running_store_revision=(
                    UUID(int=2000 + prior_sequence)
                    if prior_status is EnumGoalAttemptStatus.PASS
                    else None
                ),
                running_snapshot_sha256=(
                    _sha256(f"prior-running-{prior_sequence}".encode())
                    if prior_status is EnumGoalAttemptStatus.PASS
                    else None
                ),
                result_sha256=(
                    _sha256(f"prior-result-{prior_sequence}".encode())
                    if prior_status is EnumGoalAttemptStatus.PASS
                    else None
                ),
            )
            for prior_sequence, prior_status in enumerate(statuses[:-1], start=1)
        )
        running_revision = UUID(int=3000 + sequence)
        running_attempt = ModelGoalVerificationAttempt(
            goal_id=GOAL_ID,
            repository=REPOSITORY,
            contract_revision=CONTRACT_REVISION,
            subject_commit_sha=str(fixture["subject_commit"]),
            subject_tree_sha=str(fixture["subject_tree"]),
            attempt_id=attempt_id,
            sequence=sequence,
            status=EnumGoalAttemptStatus.RUNNING,
            execution_request_sha256=sequence_request_sha256,
        )
        running_values: dict[str, Any] = {
            "goal_id": GOAL_ID,
            "repository": REPOSITORY,
            "contract_revision": CONTRACT_REVISION,
            "subject_commit_sha": str(fixture["subject_commit"]),
            "subject_tree_sha": str(fixture["subject_tree"]),
            "allocation_count": sequence,
            "watermark_sequence": sequence,
            "store_revision": running_revision,
            "attempts": (*prior_attempts, running_attempt),
        }
        running_snapshot = ModelGoalAttemptAllocationSnapshot(
            **running_values,
            snapshot_sha256=ModelGoalAttemptAllocationSnapshot.compute_snapshot_sha256(
                **running_values
            ),
        )
        selected_attempt = ModelGoalVerificationAttempt(
            goal_id=GOAL_ID,
            repository=REPOSITORY,
            contract_revision=CONTRACT_REVISION,
            subject_commit_sha=str(fixture["subject_commit"]),
            subject_tree_sha=str(fixture["subject_tree"]),
            attempt_id=attempt_id,
            sequence=sequence,
            status=EnumGoalAttemptStatus.PASS,
            execution_request_sha256=sequence_request_sha256,
            running_store_revision=running_revision,
            running_snapshot_sha256=running_snapshot.snapshot_sha256,
            result_sha256=result_digest,
            artifact_sha256=result.artifact_sha256,
        )
        attempt_values: dict[str, Any] = {
            **running_values,
            "store_revision": UUID(int=4000 + sequence),
            "attempts": (*prior_attempts, selected_attempt),
        }
        attempts = ModelGoalAttemptAllocationSnapshot(
            **attempt_values,
            snapshot_sha256=ModelGoalAttemptAllocationSnapshot.compute_snapshot_sha256(
                **attempt_values
            ),
        )
        receipt_values: dict[str, Any] = {
            "execution_record_id": UUID(int=5000 + sequence),
            "issuer_domain": _ISSUER_DOMAIN,
            "goal_id": GOAL_ID,
            "repository": REPOSITORY,
            "contract_revision": CONTRACT_REVISION,
            "contract_schema_version": CONTRACT_SCHEMA_VERSION,
            "contract_path": "contracts/goals/example.yaml",
            "contract_source_commit_sha": str(fixture["contract_source_commit"]),
            "contract_sha256": _canonical_goal_sha256(fixture["contract"]),
            "subject_commit_sha": str(fixture["subject_commit"]),
            "subject_tree_sha": str(fixture["subject_tree"]),
            "attempt_id": attempt_id,
            "attempt_sequence": sequence,
            "running_attempt_store_revision": running_revision,
            "running_attempt_snapshot_sha256": running_snapshot.snapshot_sha256,
            "execution_request_sha256": sequence_request_sha256,
            "result_sha256": result_digest,
            "artifact_sha256": result.artifact_sha256,
            "subject_manifest_sha256": manifest.content_sha256(),
            "evaluation_observation_sha256": selected_observation.content_sha256(),
            "verifier_artifact_sha256": verifier_digest,
            "policy_revision": policy.policy_revision,
            "execution_identity": _EXECUTION_IDENTITY,
            "started_at": selected_observation.observed_at + timedelta(seconds=1),
            "completed_at": selected_observation.observed_at + timedelta(seconds=2),
            "signature": "pending-signature",
        }
        execution_receipt = ModelGoalSupervisorExecutionReceipt.model_validate(
            receipt_values
        )
        execution_receipt = execution_receipt.model_copy(
            update={
                "signature": sign_base64(
                    keypair.private_key_bytes,
                    execution_receipt.signing_payload(),
                )
            }
        )
    else:
        attempts = attempts_override or _attempt_snapshot(fixture, statuses)
    selected_attempt = attempts.attempts[-1]
    result_digest = selected_attempt.result_sha256 or _sha256(b"no-result")
    attestation_values: dict[str, Any] = {
        "attestation_id": UUID("00000000-0000-4000-8000-000000000401"),
        "issuer_domain": _ISSUER_DOMAIN,
        "goal_id": GOAL_ID,
        "repository": REPOSITORY,
        "contract_revision": CONTRACT_REVISION,
        "contract_schema_version": CONTRACT_SCHEMA_VERSION,
        "contract_path": "contracts/goals/example.yaml",
        "contract_source_commit_sha": str(fixture["contract_source_commit"]),
        "contract_sha256": _canonical_goal_sha256(fixture["contract"]),
        "subject_commit_sha": str(fixture["subject_commit"]),
        "subject_tree_sha": str(fixture["subject_tree"]),
        "attempt_id": selected_attempt.attempt_id,
        "attempt_sequence": selected_attempt.sequence,
        "attempt_result_sha256": result_digest,
        "attempt_artifact_sha256": selected_attempt.artifact_sha256,
        "execution_record_id": (
            execution_receipt.execution_record_id
            if execution_receipt is not None
            else UUID("00000000-0000-4000-8000-000000000402")
        ),
        "execution_receipt_sha256": (
            execution_receipt.content_sha256()
            if execution_receipt is not None
            else _sha256(b"missing execution receipt")
        ),
        "attempt_store_revision": attempts.store_revision,
        "attempt_snapshot_sha256": attempts.snapshot_sha256,
        "subject_manifest_sha256": manifest.content_sha256(),
        "evaluation_observation_sha256": selected_observation.content_sha256(),
        "criterion_baseline_sha256": selected_baseline.content_sha256(),
        "criterion_coverage_sha256": coverage_digest,
        "revision_history_sha256": selected_history.snapshot_sha256,
        "evaluation_observation_id": selected_observation.observation_id,
        "deadline_event_id": selected_observation.deadline_event_id,
        "verifier_artifact_sha256": verifier_digest,
        "policy_revision": _POLICY_REVISION,
        "execution_identity": _EXECUTION_IDENTITY,
        "issued_at": issued_at
        or selected_observation.observed_at + timedelta(seconds=3),
        "expires_at": expires_at
        or selected_observation.observed_at + timedelta(minutes=30),
        "signature": "pending-signature",
    }
    if attestation_override:
        attestation_values.update(attestation_override)
    attestation = ModelGoalSupervisorAttestation.model_validate(attestation_values)
    attestation = attestation.model_copy(
        update={
            "signature": sign_base64(
                keypair.private_key_bytes, attestation.signing_payload()
            )
        }
    )
    admission_observation = None
    if (
        execution_receipt is not None
        and selected_attempt.status is EnumGoalAttemptStatus.PASS
    ):
        admission_observation = ModelGoalAdmissionObservation(
            observation_id=UUID("00000000-0000-4000-8000-000000000408"),
            repository=REPOSITORY,
            goal_id=GOAL_ID,
            contract_revision=CONTRACT_REVISION,
            subject_commit_sha=str(fixture["subject_commit"]),
            subject_tree_sha=str(fixture["subject_tree"]),
            attempt_id=selected_attempt.attempt_id,
            attempt_sequence=selected_attempt.sequence,
            attempt_store_revision=attempts.store_revision,
            attempt_snapshot_sha256=attempts.snapshot_sha256,
            contract_sha256=_canonical_goal_sha256(fixture["contract"]),
            execution_record_id=execution_receipt.execution_record_id,
            execution_receipt_sha256=execution_receipt.content_sha256(),
            attestation_id=attestation.attestation_id,
            attestation_sha256=attestation.content_sha256(),
            policy_revision=policy.policy_revision,
            policy_sha256=policy.content_sha256(),
            verifier_artifact_sha256=policy.verifier_artifact_sha256,
            criterion_baseline_sha256=selected_baseline.content_sha256(),
            criterion_coverage_sha256=coverage_digest,
            revision_history_sha256=selected_history.snapshot_sha256,
            evaluation_observation_id=selected_observation.observation_id,
            evaluation_observation_sha256=selected_observation.content_sha256(),
            deadline_event_id=selected_observation.deadline_event_id,
            deadline_at=selected_observation.deadline_at,
            observed_at=selected_observation.observed_at + timedelta(seconds=4),
        )
    if (
        current_commit_source is None
        and manifest.required_subject_kind.value == "commit"
    ):
        current_commit_source = ModelGoalCommitSourceReadback(
            repository=REPOSITORY,
            goal_id=GOAL_ID,
            contract_revision=CONTRACT_REVISION,
            commit_source=manifest.commit_source,
            subject_ref=manifest.subject_ref,
            subject_repository=selected_observation.subject_repository,
            subject_commit_sha=selected_observation.subject_commit_sha,
            subject_tree_sha=selected_observation.subject_tree_sha,
            pull_request_number=selected_observation.pull_request_number,
            base_repository=selected_observation.base_repository,
            base_ref=selected_observation.base_ref,
            observed_at=selected_observation.observed_at,
        )
    if (
        current_merge_group_source is None
        and selected_observation.subject_kind.value == "merge_group"
    ):
        current_merge_group_source = ModelGoalMergeGroupSourceReadback(
            repository=REPOSITORY,
            goal_id=GOAL_ID,
            contract_revision=CONTRACT_REVISION,
            delivery_id=selected_observation.merge_group_delivery_id,
            merge_group_id=selected_observation.merge_group_id,
            merge_group_ref=selected_observation.merge_group_ref,
            base_ref=selected_observation.merge_group_base_ref,
            head_ref=selected_observation.merge_group_head_ref,
            base_sha=selected_observation.merge_group_base_sha,
            base_tree_sha=selected_observation.merge_group_base_tree_sha,
            head_sha=selected_observation.merge_group_head_sha,
            head_tree_sha=selected_observation.merge_group_head_tree_sha,
            source_checkpoint_id=selected_observation.merge_group_source_checkpoint_id,
            source_body_sha256=selected_observation.merge_group_source_body_sha256,
            received_at=selected_observation.merge_group_received_at,
            observed_at=selected_observation.observed_at + timedelta(seconds=1),
        )
    return _FullProvider(
        attempts=attempts,
        policy=policy,
        attestation=attestation,
        execution_receipt=execution_receipt,
        admission_observation=admission_observation,
        history=selected_history,
        observation=selected_observation,
        current_commit_source=current_commit_source,
        current_merge_group_source=current_merge_group_source,
        trust_root=keypair.public_key_bytes,
        artifacts={
            verifier_digest: verifier_artifact_bytes,
            **(
                {result_digest: execution_result_bytes}
                if execution_result_bytes is not None
                else {}
            ),
            **(
                dict.fromkeys(
                    execution_result.artifact_sha256 if execution_result else (),
                    b"protected goal execution artifact",
                )
            ),
        },
        ledger_key_provider=_WorkLedgerKeyProvider(
            {_WORK_LEDGER_RUNTIME_ID: _WORK_LEDGER_KEYPAIR.public_key_bytes}
        ),
        mutation_state=mutation_state
        or ModelGoalMutationState(
            repository=REPOSITORY,
            goal_id=GOAL_ID,
            store_revision=UUID("00000000-0000-4000-8000-000000000901"),
            status="clear",
        ),
    )


def _public_result(fixture: dict[str, Any], provider: _FullProvider):
    return validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )


def _commit_manifest(source: str) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "phase": "post_merge",
        "required_subject_kind": "commit",
        "commit_source": source,
        "subject_ref": (
            "refs/heads/jonah/omn-20070-goal-contract"
            if source == "pull_request"
            else "refs/heads/main"
        ),
        "dependencies": [],
        "parent_integration_criterion_id": None,
    }
    if source == "pull_request":
        manifest["base_ref"] = "refs/heads/main"
    return manifest


def _deployment_manifest() -> dict[str, Any]:
    return {
        "phase": "deployment",
        "required_subject_kind": "deployment",
        "dependencies": [],
        "parent_integration_criterion_id": None,
    }


@pytest.mark.unit
@pytest.mark.parametrize("source", ["pull_request", "branch"])
def test_public_commit_admission_requires_matching_current_source_readback(
    tmp_path: Path, source: str
) -> None:
    fixture = _coverage_fixture(
        tmp_path,
        subject_manifest=_commit_manifest(source),
    )
    valid_provider = _full_provider(fixture)

    result = _public_result(fixture, valid_provider)

    assert result.eligible is True
    assert result.evaluation_commit_source == source
    assert result.evaluation_subject_ref == _commit_manifest(source)["subject_ref"]
    assert result.evaluation_subject_repository == REPOSITORY
    assert result.evaluation_pull_request_number == (
        123 if source == "pull_request" else None
    )

    assert valid_provider.current_commit_source is not None
    mismatched_provider = _full_provider(
        fixture,
        current_commit_source=valid_provider.current_commit_source.model_copy(
            update={"subject_ref": "refs/heads/other"}
        ),
    )
    mismatch_result = _public_result(fixture, mismatched_provider)

    assert mismatch_result.eligible is False
    assert mismatch_result.reason is EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH


@pytest.mark.unit
def test_public_pull_request_readback_binds_fork_head_and_base_identity(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(
        tmp_path,
        subject_manifest=_commit_manifest("pull_request"),
    )
    initial_provider = _full_provider(fixture)
    assert initial_provider.current_commit_source is not None
    fork_observation = initial_provider.observation.model_copy(
        update={"subject_repository": "contributor/omnibase_core"}
    )
    fork_readback = initial_provider.current_commit_source.model_copy(
        update={"subject_repository": "contributor/omnibase_core"}
    )
    fork_provider = _full_provider(
        fixture,
        observation=fork_observation,
        current_commit_source=fork_readback,
    )

    fork_result = _public_result(fixture, fork_provider)

    assert fork_result.eligible is True
    assert fork_result.evaluation_subject_repository == "contributor/omnibase_core"
    assert fork_result.evaluation_base_repository == REPOSITORY
    assert fork_result.evaluation_base_ref == "refs/heads/main"

    assert fork_provider.current_commit_source is not None
    wrong_base_readback = fork_provider.current_commit_source.model_copy(
        update={"base_ref": "refs/heads/other"}
    )
    wrong_base_provider = replace(
        fork_provider, current_commit_source=wrong_base_readback
    )
    wrong_base_result = _public_result(fixture, wrong_base_provider)

    assert wrong_base_result.eligible is False
    assert wrong_base_result.reason is EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH


@pytest.mark.unit
@pytest.mark.parametrize("changed_field", ["artifact_sha256", "runtime_config_sha256"])
def test_public_deployment_admission_binds_signed_runtime_identity(
    tmp_path: Path, changed_field: str
) -> None:
    fixture = _coverage_fixture(
        tmp_path,
        subject_manifest=_deployment_manifest(),
    )
    provider = _full_provider(fixture)

    result = _public_result(fixture, provider)

    assert result.eligible is True
    assert result.evaluation_subject_kind == "deployment"
    changed_observation = provider.observation.model_copy(
        update={changed_field: _sha256(b"changed deployment identity")}
    )
    stale_provider = replace(provider, observation=changed_observation)
    stale_result = _public_result(fixture, stale_provider)

    assert stale_result.eligible is False
    assert stale_result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID


@pytest.mark.unit
def test_public_deployment_admission_blocks_persisted_expiry(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path, subject_manifest=_deployment_manifest())
    provider = _full_provider(fixture)
    deadline = provider.observation.deadline_at
    expired_observation = provider.observation.model_copy(
        update={
            "deadline_status": "expired",
            "deadline_recorded_at": deadline + timedelta(seconds=1),
        }
    )

    result = _public_result(fixture, replace(provider, observation=expired_observation))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_DEADLINE_EXPIRED


@pytest.mark.unit
@pytest.mark.parametrize("proof_kind", ["merge_result", "terminal"])
def test_premerge_public_contract_refuses_its_own_completion_dependency(
    tmp_path: Path, proof_kind: str
) -> None:
    self_dependency = ModelGoalDependencyProofPin(
        dependency_id="self-completion",
        proof_kind=proof_kind,
        repository=REPOSITORY,
        goal_id=GOAL_ID,
        contract_revision=CONTRACT_REVISION,
        contract_sha256=_sha256(b"self-referential contract"),
        subject_kind="merge_group",
        subject_commit_sha="a" * 40,
        subject_tree_sha="b" * 40,
        attestation_id=_OTHER_REVISION,
        signed_attestation_sha256=_sha256(b"self-referential attestation"),
        artifact_sha256=(_sha256(b"self-referential artifact"),),
    )
    manifest = {
        "phase": "pre_merge",
        "required_subject_kind": "merge_group",
        "dependencies": [self_dependency.model_dump(mode="json")],
        "parent_integration_criterion_id": CRITERION_ID,
    }
    fixture = _coverage_fixture(tmp_path, subject_manifest=manifest)
    provider = _full_provider(fixture)

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_CONTRACT_INVALID
    assert "dependency cycle" in result.detail


def _mutation_intent() -> tuple[ModelGoalMutationIntent, ModelGoalMutationContext]:
    head = "a" * 40
    context = ModelGoalMutationContext(
        app_integration_id=_APP_INTEGRATION_ID,
        context_name=_REQUIRED_CONTEXT,
        head_sha=head,
        contract_revision=CONTRACT_REVISION,
        attempt_id=UUID("00000000-0000-4000-8000-000000000921"),
        attempt_sequence=1,
        check_run_id="run-921",
        external_id="goal-921-attempt-1",
        request_sha256=_sha256(b"protected App check request"),
    )
    intent = ModelGoalMutationIntent(
        intent_id=UUID("00000000-0000-4000-8000-000000000911"),
        nonce=UUID("00000000-0000-4000-8000-000000000912"),
        repository=REPOSITORY,
        goal_id=GOAL_ID,
        mutation_kind="contract_revision",
        app_integration_id=_APP_INTEGRATION_ID,
        required_context_name=_REQUIRED_CONTEXT,
        current_contract_revision=CONTRACT_REVISION,
        current_contract_sha256=_sha256(b"current contract"),
        proposed_contract_revision=_OTHER_REVISION,
        proposed_contract_sha256=_sha256(b"proposed contract"),
        current_policy_revision=_POLICY_REVISION,
        current_policy_sha256=_sha256(b"current policy"),
        proposed_policy_revision=_THIRD_REVISION,
        proposed_policy_sha256=_sha256(b"proposed policy"),
        history_store_revision=UUID("00000000-0000-4000-8000-000000000913"),
        policy_store_revision=UUID("00000000-0000-4000-8000-000000000914"),
        observation_store_revision=UUID("00000000-0000-4000-8000-000000000915"),
        attempt_store_revision=UUID("00000000-0000-4000-8000-000000000916"),
        publication_store_revision=UUID("00000000-0000-4000-8000-000000000917"),
        affected_contexts=(context,),
        affected_head_shas=(head, "b" * 40),
        created_at=_OBSERVED_AT,
    )
    return intent, context


def _mixed_mutation_confirmation() -> ModelGoalMutationConfirmation:
    intent, context = _mutation_intent()
    remote_fields = {
        "app_integration_id": context.app_integration_id,
        "check_run_id": context.check_run_id,
        "conclusion": "failure",
        "context_name": context.context_name,
        "external_id": context.external_id,
        "head_sha": context.head_sha,
        "status": "completed",
        "summary": "The previous required check was blocked.",
        "title": "Blocked prior check",
    }
    remote_digest = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                remote_fields,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
    )
    readback = ModelGoalMutationContextReadback(
        intent_id=intent.intent_id,
        **remote_fields,
        remote_readback_sha256=remote_digest,
        read_at=_OBSERVED_AT + timedelta(minutes=1),
    )
    absence = ModelGoalCompleteAbsenceProof(
        app_integration_id=_APP_INTEGRATION_ID,
        repository=REPOSITORY,
        goal_id=GOAL_ID,
        context_name=_REQUIRED_CONTEXT,
        head_sha="b" * 40,
        query_sha256=_sha256(b"exact App required-check scan query"),
        page_count=1,
        records_read=0,
        total_count=0,
        terminal_cursor_sha256=_sha256(b"terminal cursor"),
        page_chain_sha256=_sha256(b"complete page chain"),
        captured_at=_OBSERVED_AT + timedelta(minutes=1),
        complete=True,
    )
    confirmation_values: dict[str, Any] = {
        "intent_id": intent.intent_id,
        "intent_sha256": intent.content_sha256(),
        "intent": intent,
        "repository": REPOSITORY,
        "goal_id": GOAL_ID,
        "outcome": "mixed",
        "issued_contexts": intent.affected_contexts,
        "readbacks": (readback,),
        "absence_proofs": (absence,),
        "confirmed_at": _OBSERVED_AT + timedelta(minutes=2),
        "confirmation_sha256": _sha256(b"placeholder confirmation"),
    }
    unsealed = ModelGoalMutationConfirmation.model_construct(**confirmation_values)
    confirmation_values["confirmation_sha256"] = unsealed.content_sha256()
    return ModelGoalMutationConfirmation.model_validate(confirmation_values)


@pytest.mark.unit
def test_mutation_confirmation_accepts_exact_mixed_blocked_and_absent_coverage() -> (
    None
):
    confirmation = _mixed_mutation_confirmation()

    assert confirmation.outcome == "mixed"
    assert len(confirmation.readbacks) == 1
    assert len(confirmation.absence_proofs) == 1
    assert confirmation.confirmation_sha256 == confirmation.content_sha256()


@pytest.mark.unit
def test_mutation_confirmation_rejects_missing_absence_proof() -> None:
    confirmation = _mixed_mutation_confirmation()
    wrong_head_proof = confirmation.absence_proofs[0].model_copy(
        update={"head_sha": "c" * 40}
    )
    incomplete = confirmation.model_copy(update={"absence_proofs": (wrong_head_proof,)})
    values = incomplete.model_dump(mode="python")
    values["confirmation_sha256"] = incomplete.content_sha256()

    with pytest.raises(ValidationError, match="absence proofs do not cover"):
        ModelGoalMutationConfirmation.model_validate(values)


@pytest.mark.unit
def test_app_readback_rejects_a_digest_that_does_not_match_remote_fields() -> None:
    confirmation = _mixed_mutation_confirmation()
    valid = confirmation.readbacks[0]

    with pytest.raises(ValidationError, match="remote readback digest"):
        ModelGoalMutationContextReadback.model_validate(
            {
                **valid.model_dump(mode="python"),
                "summary": "A different remote response than the signed digest.",
            }
        )


def _evaluate_public(fixture: dict[str, Any], provider: _FullProvider):
    return validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )


def _history_result(
    fixture: dict[str, Any],
    history: ModelGoalRevisionHistorySnapshot,
    snapshot: Any | None = None,
):
    provider = _full_provider(fixture, history=history)
    return _validate_goal_revision_history(
        snapshot or _input(fixture), history, admission_provider=provider
    )


@pytest.mark.unit
def test_protected_criterion_and_immutable_subject_fixture_match_exactly(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    baseline = ModelGoalCriterionBaseline(requirements=(_requirement(fixture),))

    reason, detail, baseline_digest, coverage_digest = _coverage(fixture, baseline)

    assert reason is None, detail
    assert baseline_digest == baseline.content_sha256()
    assert coverage_digest is not None and coverage_digest.startswith("sha256:")


@pytest.mark.unit
def test_public_resolver_requires_protected_criterion_binding(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path, binds_ac=None)
    provider = _full_provider(fixture)

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_CRITERION_COVERAGE_MISSING, (
        result.detail
    )
    assert CRITERION_ID in result.detail


@pytest.mark.unit
@pytest.mark.parametrize(
    ("check_type", "binds_ac", "expected_reason"),
    [
        (
            GOAL_CHECK_TYPE,
            (CRITERION_ID, "unprotected-criterion"),
            EnumOccEligibilityReason.GOAL_CRITERION_BASELINE_MISMATCH,
        ),
        (
            "disposition",
            (CRITERION_ID,),
            EnumOccEligibilityReason.GOAL_CRITERION_BASELINE_MISMATCH,
        ),
    ],
)
def test_public_resolver_rejects_extra_or_disposition_substitute(
    tmp_path: Path,
    check_type: str,
    binds_ac: tuple[str, ...],
    expected_reason: EnumOccEligibilityReason,
) -> None:
    fixture = _coverage_fixture(tmp_path, check_type=check_type, binds_ac=binds_ac)
    provider = _full_provider(fixture)

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is expected_reason
    assert "protected baseline" in result.detail or "exactly match" in result.detail


@pytest.mark.unit
@pytest.mark.parametrize("failure", ["absent", "changed"], ids=["missing", "altered"])
def test_public_resolver_rejects_missing_or_altered_protected_test_bytes(
    tmp_path: Path, failure: str
) -> None:
    fixture = _coverage_fixture(tmp_path)
    requirement = _requirement(
        fixture,
        file_path=(
            "tests/missing-protected-test.py"
            if failure == "absent"
            else PROTECTED_TEST_PATH
        ),
        file_bytes=(
            b"expected different protected bytes\n"
            if failure == "changed"
            else _BASELINE_TEST
        ),
    )
    provider = _full_provider(
        fixture, baseline=ModelGoalCriterionBaseline(requirements=(requirement,))
    )

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_CRITERION_BASELINE_MISMATCH
    assert "test/fixture" in result.detail


@pytest.mark.unit
def test_attestation_binds_protected_selector_and_fixture_baseline(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    provider = _full_provider(fixture)
    original = provider.policy.criterion_baseline
    assert original is not None
    changed_requirement = original.requirements[0].model_copy(
        update={
            "required_test_selectors": (f"{PROTECTED_TEST_PATH}::test_different_case",),
            "negative_control_selectors": (
                f"{PROTECTED_TEST_PATH}::test_different_case",
            ),
        }
    )
    provider.policy = provider.policy.model_copy(
        update={
            "criterion_baseline": ModelGoalCriterionBaseline(
                requirements=(changed_requirement,)
            )
        }
    )

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID
    assert "inconsistent bindings" in result.detail


@pytest.mark.unit
def test_public_resolver_accepts_complete_signed_proof_for_publisher(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    provider = _full_provider(fixture)
    selected_attempt = provider.attempts.attempts[-1]
    assert selected_attempt.result_sha256 is not None
    raw_result = provider.artifacts[selected_attempt.result_sha256]
    parsed_result = ModelGoalExecutionResult.model_validate_json(raw_result)
    assert parsed_result.attempt_id == selected_attempt.attempt_id
    assert parsed_result.content_sha256() == selected_attempt.result_sha256

    result = _public_result(fixture, provider)

    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE
    assert result.evaluation_observation_id == provider.observation.observation_id
    assert result.evaluation_deadline_status == "open"
    assert result.evaluation_deadline_recorded_at is None
    assert result.evaluation_subject_kind == "merge_group"
    assert result.evaluation_pull_request_number is None
    assert result.evaluation_merge_group_id == provider.observation.merge_group_id
    assert (
        result.evaluation_merge_group_delivery_id
        == provider.observation.merge_group_delivery_id
    )
    assert (
        result.evaluation_merge_group_source_body_sha256
        == provider.observation.merge_group_source_body_sha256
    )


@pytest.mark.unit
def test_public_resolver_requires_current_retained_merge_group_readback(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    provider = _full_provider(fixture)
    provider.current_merge_group_source = None

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE


@pytest.mark.unit
def test_public_resolver_rejects_merge_group_readback_for_another_delivery(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    provider = _full_provider(fixture)
    assert provider.current_merge_group_source is not None
    provider.current_merge_group_source = (
        provider.current_merge_group_source.model_copy(
            update={"source_body_sha256": "c" * 64}
        )
    )

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH


@pytest.mark.unit
def test_signed_execution_result_missing_required_check_fails_coverage(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path, second_item=True)
    provider = _full_provider(
        fixture,
        omit_check_keys=frozenset({(CRITERION_ID, GOAL_ITEM_ID, GOAL_CHECK_TYPE)}),
    )

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_CRITERION_COVERAGE_MISSING
    assert "exact protected criterion/check/selector baseline" in result.detail


@pytest.mark.unit
def test_public_resolver_blocks_persisted_expired_deadline_without_local_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _coverage_fixture(tmp_path)
    deadline = _OBSERVED_AT + timedelta(hours=1)
    expired_observation = ModelGoalEvaluationObservation(
        observation_id=UUID("00000000-0000-4000-8000-000000000311"),
        deadline_event_id=UUID("00000000-0000-4000-8000-000000000312"),
        repository=REPOSITORY,
        goal_id=GOAL_ID,
        contract_revision=CONTRACT_REVISION,
        subject_commit_sha=str(fixture["subject_commit"]),
        subject_tree_sha=str(fixture["subject_tree"]),
        subject_kind="merge_group",
        **_merge_group_observation_fields(fixture),
        observed_at=_OBSERVED_AT,
        deadline_at=deadline,
        deadline_status="expired",
        deadline_recorded_at=deadline + timedelta(seconds=1),
    )
    provider = _full_provider(fixture, observation=expired_observation)

    def forbid_attestation_freshness(*_: Any, **__: Any) -> bool:
        raise AssertionError(
            "persisted expiry must block before evaluating attestation freshness"
        )

    monkeypatch.setattr(
        ModelGoalSupervisorAttestation,
        "is_fresh_at",
        forbid_attestation_freshness,
    )
    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_DEADLINE_EXPIRED
    assert result.evaluation_deadline_status == "expired"
    assert result.evaluation_deadline_recorded_at == deadline + timedelta(seconds=1)


@pytest.mark.unit
def test_public_resolver_refuses_when_authoritative_mutation_snapshot_is_missing(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    provider = _full_provider(fixture)
    provider.mutation_state = None

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert "mutation barrier" in result.detail


@pytest.mark.unit
def test_public_resolver_blocks_pending_mutation_even_with_valid_signed_proof(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    intent = ModelGoalMutationIntent(
        intent_id=UUID("00000000-0000-4000-8000-000000000911"),
        nonce=UUID("00000000-0000-4000-8000-000000000912"),
        repository=REPOSITORY,
        goal_id=GOAL_ID,
        mutation_kind="contract_revision",
        app_integration_id="protected-app-installation",
        required_context_name="Goal / OMN-20070 / required",
        current_contract_revision=CONTRACT_REVISION,
        current_contract_sha256=_canonical_goal_sha256(fixture["contract"]),
        proposed_contract_revision=_OTHER_REVISION,
        proposed_contract_sha256=_sha256(b"proposed contract"),
        current_policy_revision=_POLICY_REVISION,
        current_policy_sha256=_sha256(b"current policy"),
        proposed_policy_revision=_THIRD_REVISION,
        proposed_policy_sha256=_sha256(b"proposed policy"),
        history_store_revision=UUID("00000000-0000-4000-8000-000000000913"),
        policy_store_revision=UUID("00000000-0000-4000-8000-000000000914"),
        observation_store_revision=UUID("00000000-0000-4000-8000-000000000915"),
        attempt_store_revision=UUID("00000000-0000-4000-8000-000000000916"),
        publication_store_revision=UUID("00000000-0000-4000-8000-000000000917"),
        affected_head_shas=(str(fixture["subject_commit"]),),
        created_at=_OBSERVED_AT,
    )
    state = ModelGoalMutationState(
        repository=REPOSITORY,
        goal_id=GOAL_ID,
        store_revision=UUID("00000000-0000-4000-8000-000000000918"),
        status="pending",
        intent=intent,
    )
    provider = _full_provider(fixture, mutation_state=state)

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_MUTATION_PENDING
    assert result.goal_mutation_intent_id == intent.intent_id


@pytest.mark.unit
@pytest.mark.parametrize(
    ("deadline_status", "deadline_recorded_at"),
    [
        ("expired", None),
        ("expired", _OBSERVED_AT),
        ("open", _OBSERVED_AT + timedelta(hours=1)),
    ],
    ids=[
        "expired-needs-occurrence",
        "occurrence-cannot-precede-deadline",
        "open-has-no-occurrence",
    ],
)
def test_deadline_occurrence_state_requires_a_persisted_valid_transition(
    tmp_path: Path, deadline_status: str, deadline_recorded_at: datetime | None
) -> None:
    fixture = _coverage_fixture(tmp_path)
    with pytest.raises(ValidationError):
        ModelGoalEvaluationObservation(
            observation_id=UUID("00000000-0000-4000-8000-000000000321"),
            deadline_event_id=UUID("00000000-0000-4000-8000-000000000322"),
            repository=REPOSITORY,
            goal_id=GOAL_ID,
            contract_revision=CONTRACT_REVISION,
            subject_commit_sha=str(fixture["subject_commit"]),
            subject_tree_sha=str(fixture["subject_tree"]),
            subject_kind="merge_group",
            **_merge_group_observation_fields(fixture),
            observed_at=_OBSERVED_AT,
            deadline_at=_OBSERVED_AT + timedelta(hours=1),
            deadline_status=deadline_status,
            deadline_recorded_at=deadline_recorded_at,
        )


@pytest.mark.unit
def test_public_resolver_uses_recorded_final_admission_time_not_local_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _coverage_fixture(tmp_path)
    provider = _full_provider(fixture)
    observed: list[datetime] = []

    def check_recorded_time(
        _self: ModelGoalSupervisorAttestation,
        observed_at: datetime,
        *,
        max_age_seconds: int,
    ) -> bool:
        observed.append(observed_at)
        return (
            provider.admission_observation is not None
            and observed_at == provider.admission_observation.observed_at
            and max_age_seconds == 3600
        )

    monkeypatch.setattr(
        ModelGoalSupervisorAttestation, "is_fresh_at", check_recorded_time
    )

    result = _public_result(fixture, provider)

    assert provider.admission_observation is not None
    assert observed == [provider.admission_observation.observed_at]
    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE


@pytest.mark.unit
def test_public_resolver_rejects_observation_before_attestation_issue(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    stale_observation = ModelGoalEvaluationObservation(
        observation_id=UUID("00000000-0000-4000-8000-000000000301"),
        deadline_event_id=UUID("00000000-0000-4000-8000-000000000302"),
        repository=REPOSITORY,
        goal_id=GOAL_ID,
        contract_revision=CONTRACT_REVISION,
        subject_commit_sha=str(fixture["subject_commit"]),
        subject_tree_sha=str(fixture["subject_tree"]),
        subject_kind=ModelGoalSubjectManifest.model_validate(
            fixture["contract"]["subject_manifest"]
        ).required_subject_kind,
        **{
            **_merge_group_observation_fields(fixture),
            "merge_group_received_at": _OBSERVED_AT - timedelta(hours=2, seconds=1),
        },
        observed_at=_OBSERVED_AT - timedelta(hours=2),
        deadline_at=_OBSERVED_AT - timedelta(hours=1),
    )
    provider = _full_provider(
        fixture,
        observation=stale_observation,
        issued_at=_OBSERVED_AT - timedelta(minutes=1),
        expires_at=_OBSERVED_AT + timedelta(minutes=1),
    )

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID
    assert "active protected policy or goal subject" in result.detail


@pytest.mark.unit
def test_missing_required_criterion_binding_is_not_replaced_by_disposition(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    baseline = ModelGoalCriterionBaseline(requirements=(_requirement(fixture),))
    contract = fixture["contract"]
    assert isinstance(contract, dict)
    evidence = contract["dod_evidence"]
    assert isinstance(evidence, list) and isinstance(evidence[0], dict)
    without_binding = dict(evidence[0])
    without_binding.pop("binds_ac")
    reason, detail, _, _ = _coverage(
        fixture,
        baseline,
        evidence_items=(ModelDodEvidenceItem.model_validate(without_binding),),
    )
    assert reason.value == "goal_criterion_coverage_missing"
    assert CRITERION_ID in detail

    # A human disposition item cannot stand in for the protected deterministic
    # command binding. It is an extra/mismatched check, not proof of the command.
    disposition_fixture = _coverage_fixture(
        tmp_path / "disposition", check_type="disposition"
    )
    disposition_baseline = ModelGoalCriterionBaseline(
        requirements=(_requirement(disposition_fixture, check_type=GOAL_CHECK_TYPE),)
    )
    reason, detail, _, _ = _coverage(disposition_fixture, disposition_baseline)
    assert reason.value == "goal_criterion_baseline_mismatch"
    assert "exactly match" in detail


@pytest.mark.unit
def test_extra_criterion_binding_refuses_unprotected_criteria(tmp_path: Path) -> None:
    fixture = _coverage_fixture(tmp_path)
    baseline = ModelGoalCriterionBaseline(requirements=(_requirement(fixture),))
    item = _evidence_items(fixture["contract"])[0]
    item_with_extra = item.model_copy(update={"binds_ac": (CRITERION_ID, "untrusted")})

    reason, detail, _, _ = _coverage(
        fixture, baseline, evidence_items=(item_with_extra,)
    )

    assert reason.value == "goal_criterion_baseline_mismatch"
    assert "outside the protected baseline" in detail


@pytest.mark.unit
def test_missing_protected_check_is_distinct_from_an_altered_check(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    contract = fixture["contract"]
    assert isinstance(contract, dict)
    evidence = contract["dod_evidence"]
    assert isinstance(evidence, list)
    second = {
        "id": "goal-contract-second-check",
        "description": "A second check for the same criterion.",
        "binds_ac": [CRITERION_ID],
        "checks": [{"check_type": GOAL_CHECK_TYPE, "check_value": "uv run true"}],
    }
    evidence.append(second)
    baseline = ModelGoalCriterionBaseline(
        requirements=(
            ModelGoalCriterionRequirement(
                criterion_id=CRITERION_ID,
                criterion_definition="The protected goal criterion is satisfied.",
                required_checks=(
                    ModelGoalRequiredCheckBinding(
                        item_id=GOAL_ITEM_ID,
                        check_type=EnumDodCheckType(GOAL_CHECK_TYPE),
                        check_value_sha256=compute_goal_check_value_sha256(
                            GOAL_CHECK_VALUE
                        ),
                    ),
                    ModelGoalRequiredCheckBinding(
                        item_id="goal-contract-second-check",
                        check_type=EnumDodCheckType(GOAL_CHECK_TYPE),
                        check_value_sha256=compute_goal_check_value_sha256(
                            "uv run true"
                        ),
                    ),
                ),
                required_test_selectors=(
                    f"{PROTECTED_TEST_PATH}::test_goal_criterion_is_exercised",
                ),
                negative_control_selectors=(
                    f"{PROTECTED_TEST_PATH}::test_goal_criterion_is_exercised",
                ),
                test_and_fixture_files=(
                    ModelGoalProtectedBaselineFile(
                        path=PROTECTED_TEST_PATH, sha256=_sha256(_BASELINE_TEST)
                    ),
                ),
            ),
        )
    )

    missing_reason, missing_detail, _, _ = _coverage(
        fixture,
        baseline,
        evidence_items=_evidence_items({"dod_evidence": evidence[:1]}),
    )
    altered = dict(evidence[1])
    altered["checks"] = [
        {"check_type": GOAL_CHECK_TYPE, "check_value": "uv run altered"}
    ]
    altered_reason, altered_detail, _, _ = _coverage(
        fixture,
        baseline,
        evidence_items=(
            *_evidence_items({"dod_evidence": evidence[:1]}),
            ModelDodEvidenceItem.model_validate(altered),
        ),
    )

    assert missing_reason.value == "goal_criterion_coverage_missing"
    assert "protected required checks" in missing_detail
    assert altered_reason.value == "goal_criterion_baseline_mismatch"
    assert "exactly match" in altered_detail


@pytest.mark.unit
@pytest.mark.parametrize("file_failure", ["absent", "changed"])
def test_missing_or_changed_protected_test_bytes_refuse_coverage(
    tmp_path: Path, file_failure: str
) -> None:
    fixture = _coverage_fixture(tmp_path)
    baseline_file_path = (
        "tests/does-not-exist.py" if file_failure == "absent" else PROTECTED_TEST_PATH
    )
    baseline = ModelGoalCriterionBaseline(
        requirements=(
            _requirement(
                fixture,
                file_path=baseline_file_path,
                file_bytes=b"different bytes, independent of candidate tree",
            ),
        )
    )

    reason, detail, _, _ = _coverage(fixture, baseline)

    assert reason.value == "goal_criterion_baseline_mismatch"
    assert "test/fixture" in detail


@pytest.mark.unit
def test_linear_revision_history_selects_only_its_current_leaf(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    current = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    history = _revision_history(fixture, (root, current))

    reason, detail, digest = _history_result(fixture, history)

    assert reason is None, detail
    assert digest == history.snapshot_sha256


@pytest.mark.unit
def test_unresolved_fork_blocks_current_revision_admission(tmp_path: Path) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    left = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    right = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    history = _revision_history(fixture, (root, left, right))

    reason, detail, digest = _history_result(fixture, history)

    assert reason.value == "goal_revision_fork_unresolved"
    assert "competing heads" in detail
    assert digest is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "children",
    [
        (CONTRACT_REVISION, _THIRD_REVISION),
        (CONTRACT_REVISION, _OTHER_REVISION, _THIRD_REVISION),
    ],
    ids=["omits-head", "adds-unobserved-head"],
)
def test_fork_ruling_must_name_every_competing_head_exactly(
    tmp_path: Path, children: tuple[UUID, ...]
) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    left = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    right = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    revisions = (root, left, right)
    resolution = _fork_resolution(children=children, selected=CONTRACT_REVISION)
    history = _revision_history(fixture, revisions, (resolution,))

    reason, detail, _ = _history_result(fixture, history)

    assert reason.value == "goal_revision_history_invalid"
    assert "every competing revision" in detail


@pytest.mark.unit
def test_authorized_fork_selection_makes_only_selected_leaf_current(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    selected = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    other = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    resolution = _fork_resolution(
        children=(CONTRACT_REVISION, _OTHER_REVISION), selected=CONTRACT_REVISION
    )
    history = _revision_history(fixture, (root, selected, other), (resolution,))

    reason, detail, digest = _history_result(fixture, history)

    assert reason is None, detail
    assert digest == history.snapshot_sha256

    stale_input = _input(fixture).model_copy(
        update={"contract_revision": _OTHER_REVISION}
    )
    stale_reason, stale_detail, _ = _history_result(fixture, history, stale_input)
    assert stale_reason.value == "goal_revision_not_current"
    assert "authorized current revision head" in stale_detail


@pytest.mark.unit
def test_public_resolver_refuses_unresolved_goal_revision_fork(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    selected_candidate = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    competing_candidate = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    history = _revision_history(
        fixture, (root, selected_candidate, competing_candidate)
    )
    provider = _full_provider(fixture, history=history)

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_REVISION_FORK_UNRESOLVED
    assert "competing heads" in result.detail


@pytest.mark.unit
def test_public_resolver_accepts_only_explicit_authorized_current_fork_head(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    selected = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    losing = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    ruling = _fork_resolution(
        children=(CONTRACT_REVISION, _OTHER_REVISION), selected=CONTRACT_REVISION
    )
    history = _revision_history(fixture, (root, selected, losing), (ruling,))
    provider = _full_provider(fixture, history=history)

    result = _public_result(fixture, provider)

    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE
    assert result.goal_revision_history_sha256 == history.snapshot_sha256


@pytest.mark.unit
def test_signed_work_ledger_envelope_authenticates_fork_ruling(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    selected = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    losing = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    resolution = _fork_resolution(
        children=(CONTRACT_REVISION, _OTHER_REVISION), selected=CONTRACT_REVISION
    )
    history = _revision_history(fixture, (root, selected, losing), (resolution,))
    provider = _full_provider(fixture, history=history)

    assert resolution.authorization_envelope.payload == resolution.authorization_event
    assert resolution.authorization_envelope.verify_signature(
        provider.ledger_key_provider
    )

    result = _public_result(fixture, provider)

    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE
    assert result.goal_revision_history_sha256 == history.snapshot_sha256


@pytest.mark.unit
def test_signed_but_policy_disallowed_actor_cannot_resolve_fork(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    selected = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    losing = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    spoofed_actor = ModelSessionActor(
        session_handle="unapproved-operator", agent_kind="test"
    )
    resolution = _fork_resolution(
        children=(CONTRACT_REVISION, _OTHER_REVISION),
        selected=CONTRACT_REVISION,
        actor=spoofed_actor,
    )
    history = _revision_history(fixture, (root, selected, losing), (resolution,))
    provider = _full_provider(fixture, history=history)
    assert resolution.authorization_envelope.verify_signature(
        provider.ledger_key_provider
    )

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID
    assert "authorized Work Ledger actor" in result.detail


@pytest.mark.unit
def test_authenticated_but_disallowed_event_runtime_cannot_resolve_fork(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    selected = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    losing = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    resolution = _fork_resolution(
        children=(CONTRACT_REVISION, _OTHER_REVISION),
        selected=CONTRACT_REVISION,
        runtime_id=_UNAUTHORIZED_WORK_LEDGER_RUNTIME_ID,
    )
    history = _revision_history(fixture, (root, selected, losing), (resolution,))
    provider = _full_provider(fixture, history=history)
    provider.ledger_key_provider = _WorkLedgerKeyProvider(
        {
            _WORK_LEDGER_RUNTIME_ID: _WORK_LEDGER_KEYPAIR.public_key_bytes,
            _UNAUTHORIZED_WORK_LEDGER_RUNTIME_ID: _WORK_LEDGER_KEYPAIR.public_key_bytes,
        }
    )
    assert resolution.authorization_envelope.verify_signature(
        provider.ledger_key_provider
    )

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID
    assert "fork resolution envelope signer is not authorized" in result.detail


@pytest.mark.unit
def test_tampered_signed_event_payload_cannot_resolve_fork(tmp_path: Path) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    selected = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    losing = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    resolution = _fork_resolution(
        children=(CONTRACT_REVISION, _OTHER_REVISION), selected=CONTRACT_REVISION
    )
    history = _revision_history(fixture, (root, selected, losing), (resolution,))
    tampered_event = resolution.authorization_event.model_copy(
        update={"summary": "tampered after the runtime signed the ruling"}
    )
    tampered_envelope = resolution.authorization_envelope.model_copy(
        update={"payload": tampered_event}
    )
    tampered_resolution = resolution.model_copy(
        update={
            "authorization_event": tampered_event,
            "authorization_envelope": tampered_envelope,
            "authorization_sha256": compute_goal_resolution_event_sha256(
                tampered_event
            ),
        }
    )
    history_with_tamper = history.model_copy(
        update={
            "fork_resolutions": (tampered_resolution,),
            "snapshot_sha256": _sha256(b"placeholder"),
        }
    )
    history_with_tamper = history_with_tamper.model_copy(
        update={"snapshot_sha256": history_with_tamper.content_sha256()}
    )
    provider = _full_provider(fixture, history=history_with_tamper)

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID
    assert "authentic signed Work Ledger envelope" in result.detail


@pytest.mark.unit
def test_missing_work_ledger_signing_key_cannot_resolve_fork(tmp_path: Path) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    selected = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    losing = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    resolution = _fork_resolution(
        children=(CONTRACT_REVISION, _OTHER_REVISION), selected=CONTRACT_REVISION
    )
    history = _revision_history(fixture, (root, selected, losing), (resolution,))
    provider = _full_provider(fixture, history=history)
    provider.ledger_key_provider = _WorkLedgerKeyProvider({})

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID
    assert "authentic signed Work Ledger envelope" in result.detail


@pytest.mark.unit
@pytest.mark.parametrize(
    "named_children",
    [
        (CONTRACT_REVISION, _THIRD_REVISION),
        (CONTRACT_REVISION, _OTHER_REVISION, _THIRD_REVISION),
    ],
    ids=["omitted-child", "invented-child"],
)
def test_public_resolver_requires_ruling_to_name_exact_fork_children(
    tmp_path: Path, named_children: tuple[UUID, ...]
) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    selected_candidate = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    competing_candidate = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    resolution = _fork_resolution(children=named_children, selected=CONTRACT_REVISION)
    history = _revision_history(
        fixture, (root, selected_candidate, competing_candidate), (resolution,)
    )
    provider = _full_provider(fixture, history=history)

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID
    assert "every competing revision" in result.detail


@pytest.mark.unit
def test_public_resolver_rejects_revision_outside_attempt_partition(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    current = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    losing = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    resolution = _fork_resolution(
        children=(CONTRACT_REVISION, _OTHER_REVISION),
        selected=CONTRACT_REVISION,
    )
    history = _revision_history(fixture, (root, current, losing), (resolution,))
    provider = _full_provider(fixture, history=history)
    snapshot = _input(fixture).model_copy(update={"contract_revision": _OTHER_REVISION})

    result = validate_occ_merge_eligibility(snapshot, goal_admission_provider=provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_SUBJECT_MISMATCH
    assert "another subject partition" in result.detail.lower()


@pytest.mark.unit
def test_public_resolver_blocks_missing_parent_or_cyclic_revision_history(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    orphan = _revision(CONTRACT_REVISION, fixture, parent=_OTHER_REVISION)
    orphan_provider = _full_provider(
        fixture, history=_revision_history(fixture, (root, orphan))
    )
    orphan_result = _public_result(fixture, orphan_provider)

    cyclic_one = _revision(CONTRACT_REVISION, fixture, parent=_OTHER_REVISION)
    cyclic_two = _revision(_OTHER_REVISION, fixture, parent=CONTRACT_REVISION)
    cycle_provider = _full_provider(
        fixture, history=_revision_history(fixture, (root, cyclic_one, cyclic_two))
    )
    cycle_result = _public_result(fixture, cycle_provider)

    assert orphan_result.eligible is False
    assert (
        orphan_result.reason is EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID
    )
    assert "missing predecessor" in orphan_result.detail
    assert cycle_result.eligible is False
    assert cycle_result.reason is EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID
    assert "cycle" in cycle_result.detail


@pytest.mark.unit
def test_late_fork_preserves_historical_close_but_blocks_current_ledger_state() -> None:
    """A later fork makes current state undecided without reopening old closure."""
    import uuid
    from datetime import UTC, datetime

    at = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
    claim_id = uuid.uuid4()
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    claim = ModelWorkClaimRequested(
        event_id=claim_id,
        emitted_at=at,
        actor=_WORK_ACTOR,
        ticket_id="OMN-20070",
        summary="open the goal contract",
        dod_evidence=(
            ModelContractDodItem(
                id="behavior",
                description="The original goal acceptance criterion.",
                binds_ac=("AC1",),
            ),
        ),
        contract_schema_version="1.0.0",
    )
    left = ModelWorkGoalRevised(
        event_id=left_id,
        emitted_at=at,
        actor=_WORK_ACTOR,
        ticket_id="OMN-20070",
        summary="revise criterion A",
        goal_id=claim_id,
        dod_evidence=(),
        contract_schema_version="1.0.0",
        reason="first branch",
        replaces=claim_id,
    )
    right = left.model_copy(
        update={"event_id": right_id, "reason": "late competing branch"}
    )
    closed = ModelWorkResultRecorded(
        event_id=uuid.uuid4(),
        emitted_at=at,
        actor=_WORK_ACTOR,
        ticket_id="OMN-20070",
        summary="record historical close against the first branch",
        outcome=EnumWorkOutcome.LANDED,
        closes_claims=frozenset({claim_id}),
        contract_revision=left_id,
        friction_none=True,
    )

    before_ruling = fold_work_events([claim, left, closed, right])
    assert claim not in before_ruling.open_claims
    assert any(
        "goal revision fork" in reason for reason in before_ruling.undecided_reasons
    )

    resolution = ModelWorkRulingRecorded(
        event_id=uuid.uuid4(),
        emitted_at=at,
        actor=_WORK_ACTOR,
        ticket_id="OMN-20070",
        summary="record a structured selection after the late fork",
        operator_words="Select the first branch; keep the historical close.",
        goal_revision_resolution=ModelWorkGoalRevisionResolution(
            goal_id=claim_id,
            repository=REPOSITORY,
            fork_parent_revision_id=claim_id,
            competing_revision_ids=(right_id, left_id),
            selected_revision_id=left_id,
            resolution_policy_revision=_POLICY_REVISION,
        ),
    )
    after_late_ruling = fold_work_events([claim, left, closed, right, resolution])
    reordered = fold_work_events([resolution, right, closed, left, claim])

    assert claim not in after_late_ruling.open_claims
    assert claim not in reordered.open_claims
    assert (
        after_late_ruling.goal_revision_resolution_events == (resolution,)
        or resolution in after_late_ruling.goal_revision_resolution_events
    )
    assert after_late_ruling.undecided_reasons == reordered.undecided_reasons
    assert not any(
        "goal revision fork" in reason for reason in after_late_ruling.undecided_reasons
    )


@pytest.mark.unit
def test_operator_words_alone_do_not_resolve_a_goal_revision_fork() -> None:
    """A narrative ruling without the typed selection is not authorization."""
    import uuid
    from datetime import UTC, datetime

    at = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
    claim_id = uuid.uuid4()
    first = ModelWorkClaimRequested(
        event_id=claim_id,
        emitted_at=at,
        actor=_WORK_ACTOR,
        ticket_id="OMN-20070",
        summary="open the goal contract",
        dod_evidence=(),
        contract_schema_version="1.0.0",
    )
    branch_ids = (uuid.uuid4(), uuid.uuid4())
    branches = tuple(
        ModelWorkGoalRevised(
            event_id=revision_id,
            emitted_at=at,
            actor=_WORK_ACTOR,
            ticket_id="OMN-20070",
            summary="create a branch",
            goal_id=claim_id,
            dod_evidence=(),
            contract_schema_version="1.0.0",
            reason="competing branch",
            replaces=claim_id,
        )
        for revision_id in branch_ids
    )
    prose_only = ModelWorkRulingRecorded(
        event_id=uuid.uuid4(),
        emitted_at=at,
        actor=_WORK_ACTOR,
        ticket_id="OMN-20070",
        summary="a prose-only fork note",
        operator_words="I choose the first branch.",
    )

    state = fold_work_events([first, *branches, prose_only])

    assert prose_only not in state.goal_revision_resolution_events
    assert any("goal revision fork" in reason for reason in state.undecided_reasons)


@pytest.mark.unit
def test_revision_history_rejects_missing_parent_and_cycle(tmp_path: Path) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    orphan = _revision(CONTRACT_REVISION, fixture, parent=_OTHER_REVISION)
    orphan_history = _revision_history(fixture, (root, orphan))
    orphan_reason, orphan_detail, _ = _history_result(fixture, orphan_history)

    first = _revision(CONTRACT_REVISION, fixture, parent=_OTHER_REVISION)
    second = _revision(_OTHER_REVISION, fixture, parent=CONTRACT_REVISION)
    cycle_history = _revision_history(fixture, (root, first, second))
    cycle_reason, cycle_detail, _ = _history_result(fixture, cycle_history)

    assert orphan_reason.value == "goal_revision_history_invalid"
    assert "missing predecessor" in orphan_detail
    assert cycle_reason.value == "goal_revision_history_invalid"
    assert "cycle" in cycle_detail


@pytest.mark.unit
def test_malformed_ruling_digest_and_cross_goal_ruling_are_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="authorization digest"):
        _fork_resolution(
            children=(CONTRACT_REVISION, _OTHER_REVISION),
            selected=CONTRACT_REVISION,
            authorization_sha256="not-a-digest",
        )

    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    left = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    right = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    wrong_goal_resolution = _fork_resolution(
        children=(CONTRACT_REVISION, _OTHER_REVISION),
        selected=CONTRACT_REVISION,
        goal_id=_THIRD_REVISION,
    )
    history = _revision_history(fixture, (root, left, right), (wrong_goal_resolution,))

    reason, detail, _ = _history_result(fixture, history)

    assert reason.value == "goal_revision_history_invalid"
    assert "another goal" in detail


@pytest.mark.unit
@pytest.mark.parametrize("failure", ["wrong-actor", "wrong-policy-revision"])
def test_public_resolver_requires_authorized_ruling_actor_and_policy(
    tmp_path: Path, failure: str
) -> None:
    fixture = _coverage_fixture(tmp_path)
    root = _revision(GOAL_ID, fixture, parent=None)
    left = _revision(CONTRACT_REVISION, fixture, parent=GOAL_ID)
    right = _revision(_OTHER_REVISION, fixture, parent=GOAL_ID)
    if failure == "wrong-actor":
        intruder = ModelSessionActor(
            session_handle="unauthorized-session", agent_kind="test"
        )
        resolution = _fork_resolution(
            children=(CONTRACT_REVISION, _OTHER_REVISION),
            selected=CONTRACT_REVISION,
            actor=intruder,
        )
        allowed_actor_keys = (_WORK_ACTOR.actor_key,)
    else:
        resolution = _fork_resolution(
            children=(CONTRACT_REVISION, _OTHER_REVISION),
            selected=CONTRACT_REVISION,
            policy_revision=_THIRD_REVISION,
        )
        allowed_actor_keys = (_WORK_ACTOR.actor_key,)
    history = _revision_history(
        fixture,
        (root, left, right),
        (resolution,),
        allowed_actor_keys=allowed_actor_keys,
    )
    provider = _full_provider(fixture, history=history)

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID


@pytest.mark.unit
def test_public_resolver_requires_parent_integration_even_when_child_is_green(
    tmp_path: Path,
) -> None:
    manifest = {
        "phase": "pre_merge",
        "required_subject_kind": "merge_group",
        "dependencies": [],
        "parent_integration_criterion_id": "criterion-second-required",
    }
    fixture = _coverage_fixture(tmp_path, subject_manifest=manifest, second_item=True)
    provider = _full_provider(
        fixture, failed_criterion_ids=frozenset({"criterion-second-required"})
    )

    result = _public_result(fixture, provider)
    result_digest = provider.attempts.attempts[-1].result_sha256
    assert result_digest is not None
    raw_result = provider.artifacts[result_digest]
    parsed_result = ModelGoalExecutionResult.model_validate_json(raw_result)

    outcomes = {
        item.criterion_id: item.outcome for item in parsed_result.criterion_evidence
    }
    assert outcomes == {
        CRITERION_ID: "passed",
        "criterion-second-required": "failed",
    }
    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_CRITERION_COVERAGE_MISSING
    assert "parent integration criterion" in result.detail


@pytest.mark.unit
def test_public_resolver_rejects_typed_subject_kind_mismatch(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    provider = _full_provider(
        fixture,
        observation=ModelGoalEvaluationObservation(
            observation_id=UUID("00000000-0000-4000-8000-000000000311"),
            deadline_event_id=UUID("00000000-0000-4000-8000-000000000312"),
            repository=REPOSITORY,
            goal_id=GOAL_ID,
            contract_revision=CONTRACT_REVISION,
            subject_commit_sha=str(fixture["subject_commit"]),
            subject_tree_sha=str(fixture["subject_tree"]),
            subject_kind="commit",
            commit_source="branch",
            subject_ref="refs/heads/main",
            subject_repository=REPOSITORY,
            observed_at=_OBSERVED_AT,
            deadline_at=_OBSERVED_AT + timedelta(hours=1),
        ),
    )

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID
    assert "manifest" in result.detail and "subject kind" in result.detail


@pytest.mark.unit
def test_public_resolver_requires_exact_trusted_dependency_evidence(
    tmp_path: Path,
) -> None:
    pin = ModelGoalDependencyProofPin(
        dependency_id="infra-published-core",
        proof_kind="commit_check",
        repository="OmniNode-ai/omnibase_infra",
        goal_id=_OTHER_REVISION,
        contract_revision=_THIRD_REVISION,
        contract_sha256=_sha256(b"pinned infra contract"),
        subject_kind="commit",
        subject_commit_sha="a" * 40,
        subject_tree_sha="b" * 40,
        attestation_id=_FOURTH_REVISION,
        signed_attestation_sha256=_sha256(b"pinned infra attestation"),
        artifact_sha256=(_sha256(b"pinned infra artifact"),),
    )
    manifest = {
        "phase": "pre_merge",
        "required_subject_kind": "merge_group",
        "dependencies": [pin.model_dump(mode="json")],
        "parent_integration_criterion_id": CRITERION_ID,
    }
    fixture = _coverage_fixture(tmp_path, subject_manifest=manifest)
    provider = _full_provider(
        fixture,
        policy_override={
            "dependency_issuer_bindings": (
                ModelGoalDependencyIssuerBinding(
                    dependency_id="infra-published-core",
                    issuer_domain="org.omninode.infra-release",
                ),
            )
        },
    )

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert "dependency evidence 'infra-published-core' is unavailable" in result.detail


@pytest.mark.unit
def test_public_resolver_accepts_exact_signed_cross_repository_dependency(
    tmp_path: Path,
) -> None:
    pin, dependency_evidence, trust_root, artifact = _signed_external_dependency()
    manifest = {
        "phase": "pre_merge",
        "required_subject_kind": "merge_group",
        "dependencies": [pin.model_dump(mode="json")],
        "parent_integration_criterion_id": CRITERION_ID,
    }
    fixture = _coverage_fixture(tmp_path, subject_manifest=manifest)
    provider = _full_provider(
        fixture,
        policy_override={
            "dependency_issuer_bindings": (
                ModelGoalDependencyIssuerBinding(
                    dependency_id=pin.dependency_id,
                    issuer_domain=_DEPENDENCY_ISSUER_DOMAIN,
                ),
            )
        },
    )
    provider.dependency_evidence = dependency_evidence
    provider.dependency_trust_root = trust_root
    provider.artifacts[pin.artifact_sha256[0]] = artifact

    result = _public_result(fixture, provider)

    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE
    dependency_observation = dependency_evidence.admission_observation
    assert result.dependency_admission_observation_refs == {
        pin.dependency_id: (
            dependency_observation.observation_id,
            dependency_observation.content_sha256(),
        )
    }
    dependency_ref_dict = result.as_dict()["dependency_admission_observation_refs"]
    assert dependency_ref_dict[pin.dependency_id] == {
        "observation_id": str(dependency_observation.observation_id),
        "observation_sha256": dependency_observation.content_sha256(),
    }


@pytest.mark.unit
def test_public_resolver_rejects_foreign_protected_policy_scope(
    tmp_path: Path,
) -> None:
    fixture = _coverage_fixture(tmp_path)
    provider = _full_provider(
        fixture,
        policy_override={"repository": "attacker/omnibase_core"},
    )

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID
    assert "different goal revision" in result.detail
