# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.crypto.crypto_ed25519_signer import (
    generate_keypair,
    sign_base64,
    verify_base64,
)
from omnibase_core.enums.enum_goal_attempt_status import EnumGoalAttemptStatus
from omnibase_core.enums.enum_goal_supervisor_outcome import EnumGoalSupervisorOutcome
from omnibase_core.enums.ticket.enum_dod_check_type import EnumDodCheckType
from omnibase_core.models.envelope.model_envelope_signature import (
    ModelEnvelopeSignature,
)
from omnibase_core.models.envelope.model_message_envelope import ModelMessageEnvelope
from omnibase_core.models.events.work.model_session_actor import ModelSessionActor
from omnibase_core.models.events.work.model_work_claim_requested import (
    ModelWorkClaimRequested,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem
from omnibase_core.models.validation.model_goal_attempt_allocation_snapshot import (
    ModelGoalAttemptAllocationSnapshot,
    ModelGoalVerificationAttempt,
)
from omnibase_core.models.validation.model_goal_check_execution_outcome import (
    ModelGoalCheckExecutionOutcome,
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
from omnibase_core.models.validation.model_goal_evaluation_observation import (
    ModelGoalEvaluationObservation,
)
from omnibase_core.models.validation.model_goal_execution_result import (
    ModelGoalExecutionResult,
)
from omnibase_core.models.validation.model_goal_protected_baseline_file import (
    ModelGoalProtectedBaselineFile,
)
from omnibase_core.models.validation.model_goal_required_check_binding import (
    ModelGoalRequiredCheckBinding,
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
from omnibase_core.models.validation.model_goal_supervisor_execution_request import (
    ModelGoalSupervisorExecutionRequest,
)
from omnibase_core.models.validation.model_goal_supervisor_execution_result import (
    ModelGoalSupervisorExecutionResult,
)
from omnibase_core.models.validation.model_goal_supervisor_finalization_readback import (
    ModelGoalSupervisorFinalizationReadback,
)
from omnibase_core.models.validation.model_goal_supervisor_finalization_request import (
    ModelGoalSupervisorFinalizationRequest,
)
from omnibase_core.models.validation.model_goal_supervisor_finalization_result import (
    ModelGoalSupervisorFinalizationResult,
)
from omnibase_core.models.validation.model_goal_verifier_policy import (
    ModelGoalVerifierPolicy,
)
from omnibase_core.validation.validator_occ_merge_eligibility import (
    compute_goal_criterion_coverage_sha256,
)

pytestmark = pytest.mark.unit

_FILE_DIGEST = "sha256:" + "8" * 64
_OTHER_DIGEST = "sha256:" + "9" * 64
_VERIFIER_DIGEST = "sha256:" + "7" * 64
_COMMIT = "a" * 40
_TREE = "b" * 40


def _running_request(now: datetime) -> ModelGoalSupervisorExecutionRequest:
    goal_id = uuid4()
    revision_id = goal_id
    attempt_id = uuid4()
    policy_revision = uuid4()
    contract_path = PurePosixPath("contracts/goals/sample.yaml")
    evidence = (
        ModelContractDodItem(
            id="isolation",
            description="Prove protected verifier subject binding.",
            binds_ac=("AC1",),
        ),
    )
    event = ModelWorkClaimRequested(
        event_id=goal_id,
        emitted_at=now,
        actor=ModelSessionActor(
            session_handle="protected-verifier-smoke", agent_kind="test"
        ),
        summary="Protected verifier smoke test.",
        goal_id=goal_id,
        repository="OmniNode-ai/sample",
        contract_source_commit_sha=_COMMIT,
        contract_path=contract_path,
        contract_sha256=_FILE_DIGEST,
        authorization_policy_revision=policy_revision,
        dod_evidence=evidence,
        contract_schema_version=ModelSemVer.parse("1.0.0"),
    )
    envelope = ModelMessageEnvelope[object](
        realm="ci",
        runtime_id="goal-verifier-smoke",
        bus_id="local-test",
        emitted_at=now,
        signature=ModelEnvelopeSignature(
            signer="goal-verifier-smoke",
            payload_hash="a" * 64,
            signature="AA==",
        ),
        payload=event,
    )
    contract = ModelGoalContractRevisionRecord(
        goal_id=goal_id,
        repository="OmniNode-ai/sample",
        revision_id=revision_id,
        contract_schema_version=ModelSemVer.parse("1.0.0"),
        contract_path=contract_path,
        contract_source_commit_sha=_COMMIT,
        contract_sha256=_FILE_DIGEST,
        dod_evidence=evidence,
        authorization_policy_revision=policy_revision,
        source_event=event,
        source_envelope=envelope,
    )
    manifest = ModelGoalSubjectManifest(
        phase="post_merge",
        required_subject_kind="commit",
        commit_source="branch",
        subject_ref="refs/heads/main",
    )
    baseline = ModelGoalCriterionBaseline(
        requirements=(
            ModelGoalCriterionRequirement(
                criterion_id="C1",
                criterion_definition="Run the protected test.",
                required_checks=(
                    ModelGoalRequiredCheckBinding(
                        item_id="check-1",
                        check_type=EnumDodCheckType.TEST_PASSES,
                        check_value_sha256=_FILE_DIGEST,
                    ),
                ),
                required_test_selectors=("tests/test_goal.py",),
                negative_control_selectors=("tests/test_goal.py",),
                test_and_fixture_files=(
                    ModelGoalProtectedBaselineFile(
                        path=PurePosixPath("tests/test_goal.py"), sha256=_FILE_DIGEST
                    ),
                ),
            ),
        )
    )
    policy = ModelGoalVerifierPolicy(
        repository=contract.repository,
        goal_id=goal_id,
        contract_revision=revision_id,
        policy_revision=policy_revision,
        issuer_domain="omnibase-infra-goal-supervisor",
        verifier_artifact_sha256=_VERIFIER_DIGEST,
        allowed_execution_identities=("infra-test-supervisor",),
        max_attestation_age_seconds=1800,
        criterion_baseline=baseline,
        subject_manifest=manifest,
    )
    observation = ModelGoalEvaluationObservation(
        observation_id=uuid4(),
        deadline_event_id=uuid4(),
        repository=contract.repository,
        goal_id=goal_id,
        contract_revision=revision_id,
        subject_commit_sha=_COMMIT,
        subject_tree_sha=_TREE,
        subject_kind="commit",
        commit_source="branch",
        subject_ref="refs/heads/main",
        subject_repository=contract.repository,
        observed_at=now - timedelta(seconds=10),
        deadline_at=now + timedelta(minutes=30),
    )
    history = ModelGoalRevisionHistorySnapshot.model_construct(
        repository=contract.repository,
        goal_id=goal_id,
        store_revision=uuid4(),
        revisions=(contract,),
        fork_resolutions=(),
        revision_authorization_policies=(),
        snapshot_sha256=_FILE_DIGEST,
    )
    history = history.model_copy(update={"snapshot_sha256": history.content_sha256()})
    running_attempt = ModelGoalVerificationAttempt.model_construct(
        goal_id=goal_id,
        repository=contract.repository,
        contract_revision=revision_id,
        subject_commit_sha=_COMMIT,
        subject_tree_sha=_TREE,
        attempt_id=attempt_id,
        sequence=1,
        status=EnumGoalAttemptStatus.RUNNING,
        execution_request_sha256=_FILE_DIGEST,
        running_store_revision=None,
        running_snapshot_sha256=None,
        result_sha256=None,
        artifact_sha256=(),
    )
    snapshot = ModelGoalAttemptAllocationSnapshot.model_construct(
        goal_id=goal_id,
        repository=contract.repository,
        contract_revision=revision_id,
        subject_commit_sha=_COMMIT,
        subject_tree_sha=_TREE,
        allocation_count=1,
        watermark_sequence=1,
        store_revision=uuid4(),
        attempts=(running_attempt,),
        snapshot_sha256=_FILE_DIGEST,
    )
    provisional = ModelGoalSupervisorExecutionRequest.model_construct(
        contract=contract,
        attempt_snapshot=snapshot,
        policy=policy,
        evaluation_observation=observation,
        revision_history=history,
        dispatch_idempotency_key=attempt_id,
    )
    running_attempt = running_attempt.model_copy(
        update={"execution_request_sha256": provisional.execution_plan_sha256()}
    )
    snapshot = snapshot.model_copy(update={"attempts": (running_attempt,)})
    snapshot = snapshot.model_copy(
        update={
            "snapshot_sha256": ModelGoalAttemptAllocationSnapshot.compute_snapshot_sha256(
                goal_id=snapshot.goal_id,
                repository=snapshot.repository,
                contract_revision=snapshot.contract_revision,
                subject_commit_sha=snapshot.subject_commit_sha,
                subject_tree_sha=snapshot.subject_tree_sha,
                allocation_count=snapshot.allocation_count,
                watermark_sequence=snapshot.watermark_sequence,
                store_revision=snapshot.store_revision,
                attempts=snapshot.attempts,
            )
        }
    )
    return ModelGoalSupervisorExecutionRequest.model_validate(
        {
            "contract": contract,
            "attempt_snapshot": snapshot,
            "policy": policy,
            "evaluation_observation": observation,
            "revision_history": history,
            "dispatch_idempotency_key": attempt_id,
        }
    )


def _execution_result(
    request: ModelGoalSupervisorExecutionRequest,
) -> ModelGoalSupervisorExecutionResult:
    now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    started_at = now - timedelta(minutes=1)
    result = ModelGoalExecutionResult(
        attempt_id=request.attempt_id,
        criterion_evidence=(
            ModelGoalCriterionExecutionEvidence(
                criterion_id="C1", outcome="passed", evidence_sha256=_FILE_DIGEST
            ),
        ),
        raw_check_outcomes=(
            ModelGoalCheckExecutionOutcome(
                criterion_id="C1",
                item_id="check-1",
                check_type=EnumDodCheckType.TEST_PASSES,
                check_value_sha256=_FILE_DIGEST,
                outcome="passed",
                evidence_sha256=_FILE_DIGEST,
            ),
        ),
        selector_outcomes=(
            ModelGoalSelectorExecutionOutcome(
                selector="tests/test_goal.py", outcome="passed"
            ),
        ),
        artifact_sha256=(_FILE_DIGEST,),
    )
    manifest = request.policy.subject_manifest
    assert manifest is not None
    receipt = ModelGoalSupervisorExecutionReceipt(
        execution_record_id=uuid4(),
        issuer_domain=request.policy.issuer_domain,
        goal_id=request.attempt_snapshot.goal_id,
        repository=request.attempt_snapshot.repository,
        contract_revision=request.attempt_snapshot.contract_revision,
        contract_schema_version=request.contract.contract_schema_version,
        contract_path=request.contract.contract_path,
        contract_source_commit_sha=request.contract.contract_source_commit_sha,
        contract_sha256=request.contract.contract_sha256,
        subject_commit_sha=request.attempt_snapshot.subject_commit_sha,
        subject_tree_sha=request.attempt_snapshot.subject_tree_sha,
        attempt_id=request.attempt_id,
        attempt_sequence=request.attempt_sequence,
        running_attempt_store_revision=request.attempt_snapshot.store_revision,
        running_attempt_snapshot_sha256=request.attempt_snapshot.snapshot_sha256,
        execution_request_sha256=request.execution_plan_sha256(),
        result_sha256=result.content_sha256(),
        artifact_sha256=result.artifact_sha256,
        subject_manifest_sha256=manifest.content_sha256(),
        evaluation_observation_sha256=request.evaluation_observation.content_sha256(),
        verifier_artifact_sha256=request.policy.verifier_artifact_sha256,
        policy_revision=request.policy.policy_revision,
        policy_sha256=request.policy.content_sha256(),
        execution_identity="infra-test-supervisor",
        started_at=started_at,
        completed_at=now,
        signature="test-signature",
    )
    return ModelGoalSupervisorExecutionResult(
        outcome=EnumGoalSupervisorOutcome.PASS,
        request=request,
        execution_receipt=receipt,
        execution_record_id=receipt.execution_record_id,
        execution_identity="infra-test-supervisor",
        started_at=started_at,
        completed_at=now,
        result=result,
        report_sha256=_FILE_DIGEST,
    )


def _request_for_revision(
    request: ModelGoalSupervisorExecutionRequest,
    *,
    contract: ModelGoalContractRevisionRecord,
    revision_history: ModelGoalRevisionHistorySnapshot,
    subject_commit_sha: str,
    subject_tree_sha: str,
) -> ModelGoalSupervisorExecutionRequest:
    goal_id = contract.goal_id
    repository = contract.repository
    revision_id = contract.revision_id
    policy = request.policy.model_copy(
        update={
            "repository": repository,
            "goal_id": goal_id,
            "contract_revision": revision_id,
        }
    )
    observation = request.evaluation_observation.model_copy(
        update={
            "repository": repository,
            "goal_id": goal_id,
            "contract_revision": revision_id,
            "subject_commit_sha": subject_commit_sha,
            "subject_tree_sha": subject_tree_sha,
            "subject_repository": repository,
        }
    )
    previous_snapshot = request.attempt_snapshot
    attempt = previous_snapshot.attempts[-1].model_copy(
        update={
            "goal_id": goal_id,
            "repository": repository,
            "contract_revision": revision_id,
            "subject_commit_sha": subject_commit_sha,
            "subject_tree_sha": subject_tree_sha,
            "execution_request_sha256": _FILE_DIGEST,
        }
    )
    snapshot = previous_snapshot.model_copy(
        update={
            "goal_id": goal_id,
            "repository": repository,
            "contract_revision": revision_id,
            "subject_commit_sha": subject_commit_sha,
            "subject_tree_sha": subject_tree_sha,
            "store_revision": uuid4(),
            "attempts": (attempt,),
        }
    )
    provisional = ModelGoalSupervisorExecutionRequest.model_construct(
        contract=contract,
        attempt_snapshot=snapshot,
        policy=policy,
        evaluation_observation=observation,
        revision_history=revision_history,
        dispatch_idempotency_key=request.dispatch_idempotency_key,
    )
    attempt = attempt.model_copy(
        update={"execution_request_sha256": provisional.execution_plan_sha256()}
    )
    snapshot = snapshot.model_copy(update={"attempts": (attempt,)})
    snapshot = snapshot.model_copy(
        update={
            "snapshot_sha256": ModelGoalAttemptAllocationSnapshot.compute_snapshot_sha256(
                goal_id=snapshot.goal_id,
                repository=snapshot.repository,
                contract_revision=snapshot.contract_revision,
                subject_commit_sha=snapshot.subject_commit_sha,
                subject_tree_sha=snapshot.subject_tree_sha,
                allocation_count=snapshot.allocation_count,
                watermark_sequence=snapshot.watermark_sequence,
                store_revision=snapshot.store_revision,
                attempts=snapshot.attempts,
            )
        }
    )
    return ModelGoalSupervisorExecutionRequest(
        contract=contract,
        attempt_snapshot=snapshot,
        policy=policy,
        evaluation_observation=observation,
        revision_history=revision_history,
        dispatch_idempotency_key=request.dispatch_idempotency_key,
    )


def _request_fields(
    request: ModelGoalSupervisorExecutionRequest,
    *,
    attempt_snapshot: ModelGoalAttemptAllocationSnapshot | None = None,
    policy: ModelGoalVerifierPolicy | None = None,
    evaluation_observation: ModelGoalEvaluationObservation | None = None,
    revision_history: ModelGoalRevisionHistorySnapshot | None = None,
    dispatch_idempotency_key: UUID | None = None,
) -> dict[str, object]:
    return {
        "contract": request.contract,
        "attempt_snapshot": attempt_snapshot or request.attempt_snapshot,
        "policy": policy or request.policy,
        "evaluation_observation": evaluation_observation
        or request.evaluation_observation,
        "revision_history": revision_history or request.revision_history,
        "dispatch_idempotency_key": dispatch_idempotency_key
        or request.dispatch_idempotency_key,
    }


def test_execution_plan_hash_matches_the_allocated_attempt_record() -> None:
    request = _running_request(datetime(2026, 10, 1, 12, 0, tzinfo=UTC))
    assert (
        request.attempt_snapshot.attempts[-1].execution_request_sha256
        == request.execution_plan_sha256()
    )


def test_execution_plan_hash_excludes_the_allocation_snapshot_digest() -> None:
    request = _running_request(datetime(2026, 10, 1, 12, 0, tzinfo=UTC))
    original_plan = request.execution_plan_sha256()
    original_snapshot_digest = request.attempt_snapshot.snapshot_sha256
    changed_snapshot = request.attempt_snapshot.model_copy(
        update={"store_revision": uuid4()}
    )
    changed_snapshot = changed_snapshot.model_copy(
        update={
            "snapshot_sha256": ModelGoalAttemptAllocationSnapshot.compute_snapshot_sha256(
                goal_id=changed_snapshot.goal_id,
                repository=changed_snapshot.repository,
                contract_revision=changed_snapshot.contract_revision,
                subject_commit_sha=changed_snapshot.subject_commit_sha,
                subject_tree_sha=changed_snapshot.subject_tree_sha,
                allocation_count=changed_snapshot.allocation_count,
                watermark_sequence=changed_snapshot.watermark_sequence,
                store_revision=changed_snapshot.store_revision,
                attempts=changed_snapshot.attempts,
            )
        }
    )
    restored = ModelGoalSupervisorExecutionRequest.model_validate(
        _request_fields(request, attempt_snapshot=changed_snapshot)
    )

    assert changed_snapshot.snapshot_sha256 != original_snapshot_digest
    assert restored.execution_plan_sha256() == original_plan
    assert (
        restored.attempt_snapshot.attempts[-1].execution_request_sha256 == original_plan
    )


def test_execution_plan_rejects_changed_policy_content_under_same_revision() -> None:
    request = _running_request(datetime(2026, 10, 1, 12, 0, tzinfo=UTC))
    changed_policy = request.policy.model_copy(
        update={"max_attestation_age_seconds": 3600}
    )

    assert changed_policy.policy_revision == request.policy.policy_revision
    assert changed_policy.content_sha256() != request.policy.content_sha256()
    assert request.model_copy(
        update={"policy": changed_policy}
    ).execution_plan_sha256() != (request.execution_plan_sha256())
    with pytest.raises(ValidationError, match="immutable execution plan"):
        ModelGoalSupervisorExecutionRequest.model_validate(
            _request_fields(request, policy=changed_policy)
        )

    execution = _execution_result(request)
    changed_policy_receipt = execution.execution_receipt.model_copy(
        update={"policy_sha256": changed_policy.content_sha256()}
    )
    with pytest.raises(ValidationError, match="protected policy content"):
        ModelGoalSupervisorExecutionResult.model_validate(
            {
                "outcome": execution.outcome,
                "request": execution.request,
                "execution_receipt": changed_policy_receipt,
                "execution_record_id": execution.execution_record_id,
                "execution_identity": execution.execution_identity,
                "started_at": execution.started_at,
                "completed_at": execution.completed_at,
                "result": execution.result,
                "report_sha256": execution.report_sha256,
            }
        )


def test_execution_request_rejects_wrong_dispatch_key_and_subject() -> None:
    request = _running_request(datetime(2026, 10, 1, 12, 0, tzinfo=UTC))
    wrong_key = _request_fields(request, dispatch_idempotency_key=uuid4())
    with pytest.raises(ValidationError, match="dispatch idempotency key"):
        ModelGoalSupervisorExecutionRequest.model_validate(wrong_key)

    wrong_observation = request.evaluation_observation.model_copy(
        update={"subject_commit_sha": "c" * 40}
    )
    wrong_subject = _request_fields(request, evaluation_observation=wrong_observation)
    with pytest.raises(ValidationError, match="recorded observation"):
        ModelGoalSupervisorExecutionRequest.model_validate(wrong_subject)


def test_execution_request_rejects_revision_history_for_another_goal() -> None:
    request = _running_request(datetime(2026, 10, 1, 12, 0, tzinfo=UTC))
    wrong_history = request.revision_history.model_copy(
        update={"repository": "OmniNode-ai/other"}
    )
    wrong_history = wrong_history.model_copy(
        update={"snapshot_sha256": wrong_history.content_sha256()}
    )
    with pytest.raises(ValidationError, match="revision history does not match"):
        ModelGoalSupervisorExecutionRequest.model_validate(
            _request_fields(request, revision_history=wrong_history)
        )


def test_execution_request_rejects_non_running_highest_allocation() -> None:
    request = _running_request(datetime(2026, 10, 1, 12, 0, tzinfo=UTC))
    prior_attempt = request.attempt_snapshot.attempts[-1]
    latest_attempt = prior_attempt.model_copy(
        update={
            "attempt_id": uuid4(),
            "sequence": 2,
            "status": EnumGoalAttemptStatus.ALLOCATED,
        }
    )
    snapshot = request.attempt_snapshot.model_copy(
        update={
            "attempts": (prior_attempt, latest_attempt),
            "allocation_count": 2,
            "watermark_sequence": 2,
        }
    )
    snapshot = snapshot.model_copy(
        update={
            "snapshot_sha256": ModelGoalAttemptAllocationSnapshot.compute_snapshot_sha256(
                goal_id=snapshot.goal_id,
                repository=snapshot.repository,
                contract_revision=snapshot.contract_revision,
                subject_commit_sha=snapshot.subject_commit_sha,
                subject_tree_sha=snapshot.subject_tree_sha,
                allocation_count=snapshot.allocation_count,
                watermark_sequence=snapshot.watermark_sequence,
                store_revision=snapshot.store_revision,
                attempts=snapshot.attempts,
            )
        }
    )
    with pytest.raises(ValidationError, match="durable RUNNING attempt"):
        ModelGoalSupervisorExecutionRequest.model_validate(
            _request_fields(request, attempt_snapshot=snapshot)
        )


def test_execution_request_round_trips_json_wire_formats() -> None:
    request = _running_request(datetime(2026, 10, 1, 12, 0, tzinfo=UTC))
    wire = request.model_dump_json()

    from_json = ModelGoalSupervisorExecutionRequest.model_validate_json(wire)
    from_json_dict = ModelGoalSupervisorExecutionRequest.model_validate(
        request.model_dump(mode="json")
    )

    assert from_json.model_dump_json() == wire
    assert from_json_dict.model_dump_json() == wire
    assert from_json.execution_plan_sha256() == request.execution_plan_sha256()
    assert type(from_json.contract.source_event) is type(request.contract.source_event)
    assert from_json.contract.source_event == request.contract.source_event
    assert type(from_json.contract.source_envelope.payload) is type(
        request.contract.source_event
    )
    assert (
        from_json.contract.source_envelope.payload.event_id
        == request.contract.source_event.event_id
    )
    assert (
        from_json.attempt_snapshot.attempts[-1].execution_request_sha256
        == request.execution_plan_sha256()
    )


def test_execution_result_round_trips_json_wire_formats() -> None:
    request = _running_request(datetime(2026, 10, 1, 12, 0, tzinfo=UTC))
    execution = _execution_result(request)
    wire = execution.model_dump_json()

    from_json = ModelGoalSupervisorExecutionResult.model_validate_json(wire)
    from_json_dict = ModelGoalSupervisorExecutionResult.model_validate(
        execution.model_dump(mode="json")
    )

    assert from_json.model_dump_json() == wire
    assert from_json_dict.model_dump_json() == wire
    assert from_json.request.execution_plan_sha256() == request.execution_plan_sha256()
    assert from_json.execution_receipt == execution.execution_receipt


def test_finalization_request_and_readback_round_trip_json_wire_formats() -> None:
    request = _running_request(datetime(2026, 10, 1, 12, 0, tzinfo=UTC))
    execution = _execution_result(request)
    finalization = ModelGoalSupervisorFinalizationRequest(execution=execution)
    finalization_wire = finalization.model_dump_json()
    finalization_from_json = ModelGoalSupervisorFinalizationRequest.model_validate_json(
        finalization_wire
    )
    finalization_from_json_dict = ModelGoalSupervisorFinalizationRequest.model_validate(
        finalization.model_dump(mode="json")
    )

    assert finalization_from_json.model_dump_json() == finalization_wire
    assert finalization_from_json_dict.model_dump_json() == finalization_wire
    assert (
        finalization_from_json.execution.execution_receipt
        == execution.execution_receipt
    )

    running_snapshot = request.attempt_snapshot
    running_attempt = running_snapshot.attempts[-1]
    passed_attempt = running_attempt.model_copy(
        update={
            "status": EnumGoalAttemptStatus.PASS,
            "running_store_revision": running_snapshot.store_revision,
            "running_snapshot_sha256": running_snapshot.snapshot_sha256,
            "result_sha256": execution.result.content_sha256(),
            "artifact_sha256": execution.result.artifact_sha256,
        }
    )
    completed_snapshot = running_snapshot.model_copy(
        update={"store_revision": uuid4(), "attempts": (passed_attempt,)}
    )
    completed_snapshot = completed_snapshot.model_copy(
        update={
            "snapshot_sha256": ModelGoalAttemptAllocationSnapshot.compute_snapshot_sha256(
                goal_id=completed_snapshot.goal_id,
                repository=completed_snapshot.repository,
                contract_revision=completed_snapshot.contract_revision,
                subject_commit_sha=completed_snapshot.subject_commit_sha,
                subject_tree_sha=completed_snapshot.subject_tree_sha,
                allocation_count=completed_snapshot.allocation_count,
                watermark_sequence=completed_snapshot.watermark_sequence,
                store_revision=completed_snapshot.store_revision,
                attempts=completed_snapshot.attempts,
            )
        }
    )
    readback = ModelGoalSupervisorFinalizationReadback(
        attempt_snapshot=completed_snapshot,
        result=execution.result,
        receipt=execution.execution_receipt,
    )
    readback_wire = readback.model_dump_json()
    readback_from_json = ModelGoalSupervisorFinalizationReadback.model_validate_json(
        readback_wire
    )
    readback_from_json_dict = ModelGoalSupervisorFinalizationReadback.model_validate(
        readback.model_dump(mode="json")
    )

    assert readback_from_json.model_dump_json() == readback_wire
    assert readback_from_json_dict.model_dump_json() == readback_wire
    assert (
        readback_from_json.attempt_snapshot.snapshot_sha256
        == completed_snapshot.snapshot_sha256
    )
    assert (
        readback_from_json.result.content_sha256() == execution.result.content_sha256()
    )
    assert readback_from_json.receipt == execution.execution_receipt

    manifest = request.policy.subject_manifest
    baseline = request.policy.criterion_baseline
    assert manifest is not None
    assert baseline is not None
    key_pair = generate_keypair()
    unsigned_attestation = ModelGoalSupervisorAttestation(
        attestation_id=uuid4(),
        issuer_domain=request.policy.issuer_domain,
        goal_id=request.contract.goal_id,
        repository=request.contract.repository,
        contract_revision=request.contract.revision_id,
        contract_schema_version=request.contract.contract_schema_version,
        contract_path=request.contract.contract_path,
        contract_source_commit_sha=request.contract.contract_source_commit_sha,
        contract_sha256=request.contract.contract_sha256,
        subject_commit_sha=request.attempt_snapshot.subject_commit_sha,
        subject_tree_sha=request.attempt_snapshot.subject_tree_sha,
        attempt_id=request.attempt_id,
        attempt_sequence=request.attempt_sequence,
        execution_record_id=execution.execution_record_id,
        execution_receipt_sha256=execution.execution_receipt.content_sha256(),
        attempt_result_sha256=execution.result.content_sha256(),
        attempt_artifact_sha256=execution.result.artifact_sha256,
        subject_manifest_sha256=manifest.content_sha256(),
        evaluation_observation_sha256=request.evaluation_observation.content_sha256(),
        attempt_store_revision=completed_snapshot.store_revision,
        attempt_snapshot_sha256=completed_snapshot.snapshot_sha256,
        criterion_baseline_sha256=baseline.content_sha256(),
        criterion_coverage_sha256=compute_goal_criterion_coverage_sha256(
            evidence_items=request.contract.dod_evidence,
            baseline=baseline,
        ),
        revision_history_sha256=request.revision_history.snapshot_sha256,
        evaluation_observation_id=request.evaluation_observation.observation_id,
        deadline_event_id=request.evaluation_observation.deadline_event_id,
        verifier_artifact_sha256=request.policy.verifier_artifact_sha256,
        policy_revision=request.policy.policy_revision,
        policy_sha256=request.policy.content_sha256(),
        execution_identity=execution.execution_identity,
        issued_at=execution.completed_at,
        expires_at=execution.completed_at
        + timedelta(seconds=request.policy.max_attestation_age_seconds),
        signature="AA==",
    )
    attestation_signature = sign_base64(
        key_pair.private_key_bytes, unsigned_attestation.signing_payload()
    )
    attestation = unsigned_attestation.model_copy(
        update={"signature": attestation_signature}
    )
    assert verify_base64(
        key_pair.public_key_bytes,
        attestation.signing_payload(),
        attestation.signature,
    )
    finalization_result = ModelGoalSupervisorFinalizationResult(
        finalization=finalization,
        completed_attempt_snapshot=completed_snapshot,
        attestation=attestation,
        trusted_observation_id=request.evaluation_observation.observation_id,
    )
    finalization_result_wire = finalization_result.model_dump_json()
    result_from_json = ModelGoalSupervisorFinalizationResult.model_validate_json(
        finalization_result_wire
    )
    result_from_json_dict = ModelGoalSupervisorFinalizationResult.model_validate(
        finalization_result.model_dump(mode="json")
    )

    for restored in (result_from_json, result_from_json_dict):
        assert restored.model_dump_json() == finalization_result_wire
        assert restored.attestation == attestation
        assert verify_base64(
            key_pair.public_key_bytes,
            restored.attestation.signing_payload(),
            restored.attestation.signature,
        )
        assert (
            restored.attestation.attempt_snapshot_sha256
            == completed_snapshot.snapshot_sha256
        )
        assert (
            restored.attestation.execution_receipt_sha256
            == execution.execution_receipt.content_sha256()
        )
        assert (
            restored.attestation.attempt_result_sha256
            == execution.result.content_sha256()
        )

    changed_policy = request.policy.model_copy(
        update={"max_attestation_age_seconds": 3600}
    )
    assert changed_policy.policy_revision == request.policy.policy_revision
    changed_policy_attestation = attestation.model_copy(
        update={"policy_sha256": changed_policy.content_sha256()}
    )
    with pytest.raises(ValidationError, match="final attestation does not bind"):
        ModelGoalSupervisorFinalizationResult.model_validate(
            {
                "finalization": finalization_result.finalization,
                "completed_attempt_snapshot": finalization_result.completed_attempt_snapshot,
                "attestation": changed_policy_attestation,
                "trusted_observation_id": finalization_result.trusted_observation_id,
            }
        )


def test_finalization_request_rejects_receipt_not_binding_the_result() -> None:
    request = _running_request(datetime(2026, 10, 1, 12, 0, tzinfo=UTC))
    execution = _execution_result(request)
    assert ModelGoalSupervisorFinalizationRequest(execution=execution)

    bad_receipt = execution.execution_receipt.model_copy(
        update={"result_sha256": _OTHER_DIGEST}
    )
    bad_execution = execution.model_copy(update={"execution_receipt": bad_receipt})
    with pytest.raises(ValidationError, match="detached receipt does not bind"):
        ModelGoalSupervisorFinalizationRequest.model_validate(
            {"execution": bad_execution}
        )


def test_supervisor_outcomes_keep_the_canonical_wire_values() -> None:
    assert tuple(outcome.value for outcome in EnumGoalSupervisorOutcome) == (
        "pass",
        "fail",
        "error",
        "incomplete",
    )
    assert EnumGoalSupervisorOutcome("pass") is EnumGoalSupervisorOutcome.PASS
