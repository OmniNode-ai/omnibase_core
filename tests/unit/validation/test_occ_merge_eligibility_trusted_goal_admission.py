# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Trusted supervisor admission controls for OR.2 goal-mode OCC resolution."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from omnibase_core.crypto.crypto_ed25519_signer import generate_keypair
from omnibase_core.enums.enum_goal_attempt_status import EnumGoalAttemptStatus
from omnibase_core.enums.enum_occ_eligibility_reason import EnumOccEligibilityReason
from omnibase_core.errors.error_goal_admission_provider import (
    GoalAdmissionProviderError,
)
from omnibase_core.models.validation.model_goal_admission_observation import (
    ModelGoalAdmissionObservation,
)
from omnibase_core.models.validation.model_goal_attempt_allocation_snapshot import (
    ModelGoalAttemptAllocationSnapshot,
)
from omnibase_core.models.validation.model_goal_mutation_state import (
    ModelGoalMutationState,
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
from omnibase_core.models.validation.model_occ_eligibility_input import (
    ModelOccEligibilityInput,
)
from omnibase_core.validation.validator_occ_merge_eligibility import (
    validate_occ_merge_eligibility,
)
from tests.unit.validation.test_occ_merge_eligibility_identity import (
    CONTRACT_REVISION,
    CONTRACT_SCHEMA_VERSION,
    GOAL_ID,
    REPOSITORY,
    _canonical_goal_sha256,
    _goal_repo,
    _goal_snapshot_fields,
)

_ISSUER_DOMAIN = "org.omninode.supervisor"
_EXECUTION_IDENTITY = "github-actions/goal-verifier"
_POLICY_REVISION = UUID("00000000-0000-4000-8000-000000000451")
_ARTIFACT_BYTES = b"protected goal verifier fixture"


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _input(fixture: dict[str, Any]) -> ModelOccEligibilityInput:
    from tests.unit.validation.test_occ_merge_eligibility_identity import (
        _add_protected_test_source,
    )

    _add_protected_test_source(fixture)
    repo_root = fixture["repo_root"]
    assert isinstance(repo_root, Path)
    contract = fixture["contract"]
    assert isinstance(contract, dict)
    fields = _goal_snapshot_fields(repo_root)
    # Attempt state is not part of caller-controlled eligibility input. The
    # provider supplies the current complete allocation snapshot separately.
    fields.pop("attempt_allocation", None)
    fields.update(
        {
            "repo": REPOSITORY,
            "goal_id": GOAL_ID,
            "goal_ticket_id": None,
            "contract_revision": CONTRACT_REVISION,
            "contract_schema_version": CONTRACT_SCHEMA_VERSION,
            "goal_contract_root": repo_root,
            "goal_contract_path": PurePosixPath("contracts/goals/example.yaml"),
            "goal_contract_source_commit_sha": fixture["contract_source_commit"],
            "goal_contract_sha256": _canonical_goal_sha256(contract),
            "subject_commit_sha": fixture["subject_commit"],
            "subject_tree_sha": fixture["subject_tree"],
            "pr_commit_shas": (fixture["subject_commit"],),
            "pr_body": "",
        }
    )
    manifest = contract.get("subject_manifest")
    assert isinstance(manifest, dict)
    if (
        manifest.get("required_subject_kind") != "commit"
        or manifest.get("commit_source") != "pull_request"
    ):
        fields.update(
            {
                "pr_number": None,
                "pr_title": "",
                "pr_branch": "",
                "pr_commit_shas": (),
                "pr_commit_texts": (),
            }
        )
    return ModelOccEligibilityInput.model_validate(fields)


def _attempt_snapshot(
    fixture: dict[str, Any],
    statuses: tuple[EnumGoalAttemptStatus, ...] = (EnumGoalAttemptStatus.PASS,),
    *,
    artifact_sha256: tuple[str, ...] = (),
) -> ModelGoalAttemptAllocationSnapshot:
    attempts = tuple(
        ModelGoalVerificationAttempt(
            goal_id=GOAL_ID,
            repository=REPOSITORY,
            contract_revision=CONTRACT_REVISION,
            subject_commit_sha=str(fixture["subject_commit"]),
            subject_tree_sha=str(fixture["subject_tree"]),
            attempt_id=UUID(int=sequence),
            sequence=sequence,
            status=status,
            execution_request_sha256=_sha256(f"request-{sequence}".encode()),
            running_store_revision=(
                UUID(int=1000 + sequence)
                if status is EnumGoalAttemptStatus.PASS
                else None
            ),
            running_snapshot_sha256=(
                _sha256(f"running-{sequence}".encode())
                if status is EnumGoalAttemptStatus.PASS
                else None
            ),
            result_sha256=_sha256(f"result-{sequence}".encode())
            if status is EnumGoalAttemptStatus.PASS
            else None,
            artifact_sha256=artifact_sha256,
        )
        for sequence, status in enumerate(statuses, start=1)
    )
    values: dict[str, Any] = {
        "goal_id": GOAL_ID,
        "repository": REPOSITORY,
        "contract_revision": CONTRACT_REVISION,
        "subject_commit_sha": str(fixture["subject_commit"]),
        "subject_tree_sha": str(fixture["subject_tree"]),
        "allocation_count": len(attempts),
        "watermark_sequence": len(attempts),
        "store_revision": UUID(int=451),
        "attempts": attempts,
    }
    return ModelGoalAttemptAllocationSnapshot(
        **values,
        snapshot_sha256=ModelGoalAttemptAllocationSnapshot.compute_snapshot_sha256(
            **values
        ),
    )


@dataclass
class _AdmissionProvider:
    """Test-only port fixture; trust values are not read from candidate input."""

    attempts: ModelGoalAttemptAllocationSnapshot | None
    policy: ModelGoalVerifierPolicy | None
    attestation: ModelGoalSupervisorAttestation | None
    trust_root: bytes | None
    artifacts: dict[str, bytes]
    execution_receipt: ModelGoalSupervisorExecutionReceipt | None = None

    def read_current_goal_mutation_state(self, **_: Any) -> ModelGoalMutationState:
        return ModelGoalMutationState(
            repository=REPOSITORY,
            goal_id=GOAL_ID,
            store_revision=UUID("00000000-0000-4000-8000-000000000902"),
            status="clear",
        )

    def read_current_attempt_snapshot(
        self,
        *,
        repository: str,
        goal_id: UUID,
        contract_revision: UUID,
        subject_commit_sha: str,
        subject_tree_sha: str,
    ) -> ModelGoalAttemptAllocationSnapshot | None:
        assert repository == REPOSITORY
        assert goal_id == GOAL_ID
        assert contract_revision == CONTRACT_REVISION
        assert self.attempts is None or (
            self.attempts.subject_commit_sha == subject_commit_sha
            and self.attempts.subject_tree_sha == subject_tree_sha
        )
        return self.attempts

    def get_policy(
        self,
        *,
        repository: str,
        goal_id: UUID,
        contract_revision: UUID,
    ) -> ModelGoalVerifierPolicy | None:
        assert (repository, goal_id, contract_revision) == (
            REPOSITORY,
            GOAL_ID,
            CONTRACT_REVISION,
        )
        return self.policy

    def get_attestation(
        self,
        *,
        repository: str,
        goal_id: UUID,
        contract_revision: UUID,
        subject_commit_sha: str,
        subject_tree_sha: str,
        attempt_id: UUID,
        attempt_sequence: int,
        store_revision: UUID,
    ) -> ModelGoalSupervisorAttestation | None:
        assert (repository, goal_id, contract_revision) == (
            REPOSITORY,
            GOAL_ID,
            CONTRACT_REVISION,
        )
        if self.attestation is None:
            return None
        # The fixture deliberately returns stale/mismatched records in negative
        # tests so the resolver, not the test provider, has to reject them.
        return self.attestation

    def get_domain_trust_root(self, domain_id: str) -> bytes | None:
        assert domain_id == _ISSUER_DOMAIN
        return self.trust_root

    def read_artifact_bytes(self, digest: str) -> bytes | None:
        return self.artifacts.get(digest)


def _trusted_provider(
    fixture: dict[str, Any],
    *,
    statuses: tuple[EnumGoalAttemptStatus, ...] = (EnumGoalAttemptStatus.PASS,),
    artifact_bytes: bytes | None = None,
    policy_override: dict[str, Any] | None = None,
    attestation_override: dict[str, Any] | None = None,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    artifact_digest: str | None = None,
) -> tuple[_AdmissionProvider, ModelGoalAttemptAllocationSnapshot]:
    from tests.unit.validation.test_occ_merge_eligibility_goal_coverage_revision import (
        _full_provider,
    )
    from tests.unit.validation.test_occ_merge_eligibility_identity import (
        _add_protected_test_source,
    )

    _add_protected_test_source(fixture)
    provider = _full_provider(
        fixture,
        statuses=statuses,
        attestation_override=attestation_override,
        issued_at=issued_at,
        expires_at=expires_at,
        verifier_artifact_bytes=(artifact_bytes or _ARTIFACT_BYTES),
    )
    if policy_override:
        provider.policy = provider.policy.model_copy(update=policy_override)
    if artifact_digest:
        # This helper parameter is retained for the attempt-artifact falsifier.
        # The current tests do not use it; callers should prefer a complete
        # attempt snapshot fixture when adding artifact-bound cases.
        provider.artifacts.pop(artifact_digest, None)
    return provider, provider.attempts


def _evaluate(fixture: dict[str, Any], provider: _AdmissionProvider | None) -> Any:
    return validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "newer_status",
    [
        EnumGoalAttemptStatus.ALLOCATED,
        EnumGoalAttemptStatus.RUNNING,
        EnumGoalAttemptStatus.FAIL,
        EnumGoalAttemptStatus.CANCELLED,
        EnumGoalAttemptStatus.TIMED_OUT,
        EnumGoalAttemptStatus.MISSING,
    ],
)
def test_newer_authoritative_unfinished_attempt_overrides_candidate_old_pass(
    tmp_path: Path, newer_status: EnumGoalAttemptStatus
) -> None:
    fixture = _goal_repo(tmp_path)
    provider, current = _trusted_provider(
        fixture,
        statuses=(EnumGoalAttemptStatus.PASS, newer_status),
    )
    fields = _input(fixture).model_dump()
    # An old caller-provided PASS cannot be injected as a snapshot override.
    fields["attempt_allocation"] = _attempt_snapshot(fixture)
    with pytest.raises(ValidationError, match="extra"):
        ModelOccEligibilityInput.model_validate(fields)

    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTEMPT_NONPASS
    assert result.attempt_id == current.attempts[-1].attempt_id
    assert result.attempt_sequence == 2
    assert result.attempt_watermark_sequence == 2


@pytest.mark.unit
def test_provider_missing_or_snapshot_missing_fails_closed(tmp_path: Path) -> None:
    fixture = _goal_repo(tmp_path)
    snapshot = _input(fixture)

    absent = validate_occ_merge_eligibility(snapshot)
    no_store = _AdmissionProvider(
        attempts=None,
        policy=None,
        attestation=None,
        trust_root=None,
        artifacts={},
        execution_receipt=None,
    )
    missing_snapshot = validate_occ_merge_eligibility(
        snapshot, goal_admission_provider=no_store
    )

    assert absent.eligible is False
    assert absent.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert "provider" in absent.detail.lower() or "snapshot" in absent.detail.lower()
    assert missing_snapshot.eligible is False
    assert missing_snapshot.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert "no durable attempt allocation" in missing_snapshot.detail.lower()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("missing_part", "expected_detail"),
    [
        ("policy", "no protected goal verifier policy"),
        ("attestation", "no trusted supervisor attestation"),
        ("trust_root", "no active trusted key"),
    ],
)
def test_missing_protected_trust_component_fails_closed(
    tmp_path: Path, missing_part: str, expected_detail: str
) -> None:
    fixture = _goal_repo(tmp_path)
    provider, _ = _trusted_provider(fixture)
    assert provider.attempts is not None
    setattr(provider, missing_part, None)

    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert expected_detail in result.detail


@pytest.mark.unit
def test_matching_execution_identity_from_unauthenticated_channel_is_not_trusted(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    provider, _ = _trusted_provider(fixture)
    assert provider.execution_receipt is not None
    assert provider.execution_receipt.execution_identity == _EXECUTION_IDENTITY

    # Repeating the protected verifier identity cannot authenticate a receipt.
    provider.execution_receipt = provider.execution_receipt.model_copy(
        update={"signature": "forged on an unauthenticated channel"}
    )
    provider.attestation = None

    result = _evaluate(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert "no trusted supervisor attestation" in result.detail


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("issuer_domain", "org.attacker"),
        ("execution_identity", "unapproved-runner"),
        ("contract_schema_version", "9.9.9"),
        ("verifier_artifact_sha256", _sha256(b"other verifier")),
        ("contract_sha256", _sha256(b"other contract")),
        ("subject_tree_sha", "f" * 40),
    ],
)
def test_signed_attestation_with_mismatched_claim_fails_closed(
    tmp_path: Path, field: str, value: str
) -> None:
    fixture = _goal_repo(tmp_path)
    provider, _ = _trusted_provider(fixture, attestation_override={field: value})
    assert provider.attempts is not None

    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID
    assert "does not match the active protected policy" in result.detail


@pytest.mark.unit
def test_attestation_tampering_after_signature_fails_closed(tmp_path: Path) -> None:
    fixture = _goal_repo(tmp_path)
    provider, _ = _trusted_provider(fixture)
    assert provider.attempts is not None
    assert provider.attestation is not None
    assert provider.admission_observation is not None
    provider.attestation = provider.attestation.model_copy(
        update={"signature": "tampered-after-signing"}
    )
    provider.admission_observation = provider.admission_observation.model_copy(
        update={"attestation_sha256": provider.attestation.content_sha256()}
    )

    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID
    assert "signature is invalid" in result.detail


@pytest.mark.unit
@pytest.mark.parametrize(
    ("issued_offset", "expiry_offset"),
    [
        (timedelta(seconds=3), timedelta(seconds=3, milliseconds=500)),
        (timedelta(seconds=5), timedelta(hours=1)),
    ],
    ids=["expired", "issued-in-future"],
)
def test_stale_or_future_signed_attestation_fails_closed(
    tmp_path: Path, issued_offset: timedelta, expiry_offset: timedelta
) -> None:
    from tests.unit.validation.test_occ_merge_eligibility_goal_coverage_revision import (
        _OBSERVED_AT,
    )

    fixture = _goal_repo(tmp_path)
    issued_at = _OBSERVED_AT + issued_offset
    provider, _ = _trusted_provider(
        fixture,
        issued_at=issued_at,
        expires_at=_OBSERVED_AT + expiry_offset,
    )
    assert provider.attempts is not None

    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID
    assert "does not match the active protected policy" in result.detail


@pytest.mark.unit
def test_wrong_domain_trust_root_cannot_verify_real_ed25519_signature(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    provider, _ = _trusted_provider(fixture)
    assert provider.attempts is not None
    provider.trust_root = generate_keypair().public_key_bytes

    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID
    assert "signature is invalid" in result.detail


@pytest.mark.unit
def test_verifier_artifact_bytes_must_match_protected_digest(tmp_path: Path) -> None:
    fixture = _goal_repo(tmp_path)
    provider, _ = _trusted_provider(fixture, artifact_bytes=b"tampered verifier")
    assert provider.attempts is not None

    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID
    assert "artifact bytes do not match" in result.detail


@pytest.mark.unit
def test_missing_retained_execution_result_r_fails_closed(tmp_path: Path) -> None:
    fixture = _goal_repo(tmp_path)
    provider, attempts = _trusted_provider(fixture)
    result_digest = attempts.attempts[-1].result_sha256
    assert result_digest is not None
    provider.artifacts.pop(result_digest)

    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert "execution result R could not be validated" in result.detail


@pytest.mark.unit
def test_tampered_retained_execution_result_r_fails_closed(tmp_path: Path) -> None:
    fixture = _goal_repo(tmp_path)
    provider, attempts = _trusted_provider(fixture)
    result_digest = attempts.attempts[-1].result_sha256
    assert result_digest is not None
    provider.artifacts[result_digest] = b'{"attempt_id":"tampered"}'

    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert "execution result R could not be validated" in result.detail


@pytest.mark.unit
def test_missing_isolated_execution_receipt_fails_closed(tmp_path: Path) -> None:
    fixture = _goal_repo(tmp_path)
    provider, _ = _trusted_provider(fixture)
    provider.execution_receipt = None

    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert "no isolated-execution receipt" in result.detail


@pytest.mark.unit
def test_tampered_execution_receipt_subject_binding_fails_closed(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    provider, _ = _trusted_provider(fixture)
    assert provider.execution_receipt is not None
    provider.execution_receipt = provider.execution_receipt.model_copy(
        update={"subject_tree_sha": "f" * 40}
    )

    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID
    assert "signature" in result.detail.lower() or "binding" in result.detail.lower()


@pytest.mark.unit
def test_attestation_for_older_pass_cannot_authorize_newer_pass_attempt(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    provider, attempts = _trusted_provider(
        fixture,
        statuses=(EnumGoalAttemptStatus.PASS, EnumGoalAttemptStatus.PASS),
    )
    assert provider.attestation is not None
    old_pass = attempts.attempts[0]
    stale_values = provider.attestation.model_dump(mode="json")
    stale_values.update(
        {
            "attempt_id": old_pass.attempt_id,
            "attempt_sequence": old_pass.sequence,
            "attempt_result_sha256": old_pass.result_sha256,
            "attempt_artifact_sha256": old_pass.artifact_sha256,
        }
    )
    provider.attestation = ModelGoalSupervisorAttestation.model_validate(stale_values)

    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID
    assert "does not match the active protected policy" in result.detail
    assert result.attempt_id == attempts.attempts[-1].attempt_id
    assert result.attempt_sequence == 2


@pytest.mark.unit
def test_valid_signed_admission_with_complete_coverage_is_eligible(
    tmp_path: Path,
) -> None:
    """A complete signed proof yields eligibility for Market's publisher."""
    fixture = _goal_repo(tmp_path)
    provider, attempts = _trusted_provider(fixture)
    assert provider.execution_receipt is not None
    assert provider.attestation is not None
    assert provider.admission_observation is not None
    assert (
        provider.observation.observed_at
        <= provider.execution_receipt.started_at
        <= provider.execution_receipt.completed_at
        <= provider.attestation.issued_at
        <= provider.admission_observation.observed_at
        <= provider.observation.deadline_at
    )

    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE
    assert result.attempt_id == attempts.attempts[-1].attempt_id
    assert result.attempt_sequence == attempts.watermark_sequence
    assert result.attempt_snapshot_sha256 == attempts.snapshot_sha256
    assert provider.admission_observation is not None
    assert (
        result.admission_observation_id == provider.admission_observation.observation_id
    )
    assert (
        result.admission_observation_sha256
        == provider.admission_observation.content_sha256()
    )
    serialized_result = result.as_dict()
    assert serialized_result["admission_observation_id"] == str(
        provider.admission_observation.observation_id
    )
    assert serialized_result["admission_observation_sha256"] == (
        provider.admission_observation.content_sha256()
    )
    assert (
        ModelGoalAdmissionObservation.model_validate_json(
            provider.admission_observation.canonical_json()
        )
        == provider.admission_observation
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "timing_case",
    [
        "issued_before_completion",
        "issued_after_final_observation",
        "expired",
    ],
)
def test_signed_admission_requires_fresh_post_execution_attestation(
    tmp_path: Path, timing_case: str
) -> None:
    from tests.unit.validation.test_occ_merge_eligibility_goal_coverage_revision import (
        _OBSERVED_AT,
    )

    fixture = _goal_repo(tmp_path)
    if timing_case == "issued_before_completion":
        issued_at = _OBSERVED_AT + timedelta(seconds=1)
        expires_at = _OBSERVED_AT + timedelta(minutes=30)
    elif timing_case == "issued_after_final_observation":
        issued_at = _OBSERVED_AT + timedelta(seconds=5)
        expires_at = _OBSERVED_AT + timedelta(minutes=30)
    else:
        issued_at = _OBSERVED_AT + timedelta(seconds=3)
        expires_at = _OBSERVED_AT + timedelta(seconds=3, milliseconds=500)
    provider, _ = _trusted_provider(
        fixture,
        issued_at=issued_at,
        expires_at=expires_at,
    )

    result = _evaluate(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID


@pytest.mark.unit
def test_final_admission_observation_must_match_the_signed_subject(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    provider, _ = _trusted_provider(fixture)
    assert provider.admission_observation is not None
    provider.admission_observation = provider.admission_observation.model_copy(
        update={"subject_tree_sha": "f" * 40}
    )

    result = _evaluate(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID


@pytest.mark.unit
def test_final_admission_observation_cannot_predate_attestation_issuance(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    provider, _ = _trusted_provider(fixture)
    assert provider.attestation is not None
    assert provider.admission_observation is not None
    provider.admission_observation = provider.admission_observation.model_copy(
        update={"observed_at": provider.attestation.issued_at - timedelta(seconds=1)}
    )

    result = _evaluate(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ATTESTATION_INVALID


@pytest.mark.unit
def test_missing_current_final_admission_observation_fails_closed(
    tmp_path: Path,
) -> None:
    fixture = _goal_repo(tmp_path)
    provider, _ = _trusted_provider(fixture)
    provider.admission_observation = None

    result = _evaluate(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_INCOMPLETE
    assert "no current protected final-admission observation" in result.detail


@pytest.mark.unit
def test_protected_provider_backend_failure_is_unavailable(tmp_path: Path) -> None:
    fixture = _goal_repo(tmp_path)
    provider, _ = _trusted_provider(fixture)
    assert provider.attempts is not None

    def fail_policy(**_: Any) -> None:
        raise GoalAdmissionProviderError("protected policy backend unavailable")

    provider.get_policy = fail_policy  # type: ignore[method-assign]
    result = validate_occ_merge_eligibility(
        _input(fixture), goal_admission_provider=provider
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_ADMISSION_UNAVAILABLE
    assert "policy could not be read" in result.detail
