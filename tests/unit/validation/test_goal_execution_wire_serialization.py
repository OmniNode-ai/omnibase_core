# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from uuid import UUID

from omnibase_core.crypto.crypto_ed25519_signer import (
    generate_keypair,
    sign_base64,
    verify_base64,
)
from omnibase_core.enums.ticket.enum_dod_check_type import EnumDodCheckType
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.validation.model_goal_check_execution_outcome import (
    ModelGoalCheckExecutionOutcome,
)
from omnibase_core.models.validation.model_goal_criterion_execution_evidence import (
    ModelGoalCriterionExecutionEvidence,
)
from omnibase_core.models.validation.model_goal_execution_result import (
    ModelGoalExecutionResult,
)
from omnibase_core.models.validation.model_goal_selector_execution_outcome import (
    ModelGoalSelectorExecutionOutcome,
)
from omnibase_core.models.validation.model_goal_supervisor_execution_receipt import (
    ModelGoalSupervisorExecutionReceipt,
)

_HASH_A = "sha256:" + "a" * 64
_HASH_B = "sha256:" + "b" * 64


def _execution_result() -> ModelGoalExecutionResult:
    return ModelGoalExecutionResult(
        attempt_id=UUID("00000000-0000-4000-8000-000000000104"),
        criterion_evidence=(
            ModelGoalCriterionExecutionEvidence(
                criterion_id="AC1", outcome="passed", evidence_sha256=_HASH_A
            ),
        ),
        raw_check_outcomes=(
            ModelGoalCheckExecutionOutcome(
                criterion_id="AC1",
                item_id="dod-001",
                check_type=EnumDodCheckType.COMMAND,
                check_value_sha256=_HASH_B,
                outcome="passed",
                evidence_sha256=_HASH_A,
            ),
        ),
        selector_outcomes=(
            ModelGoalSelectorExecutionOutcome(
                selector="tests/test_goal.py::test_criterion", outcome="passed"
            ),
        ),
        artifact_sha256=(_HASH_B, _HASH_A),
    )


def _execution_receipt() -> ModelGoalSupervisorExecutionReceipt:
    started_at = datetime(2026, 9, 30, 12, 30, tzinfo=UTC)
    return ModelGoalSupervisorExecutionReceipt(
        execution_record_id=UUID("00000000-0000-4000-8000-000000000101"),
        issuer_domain="org.omninode.supervisor",
        goal_id=UUID("00000000-0000-4000-8000-000000000102"),
        repository="OmniNode-ai/omnimarket",
        contract_revision=UUID("00000000-0000-4000-8000-000000000103"),
        contract_schema_version=ModelSemVer.parse("1.0.0"),
        contract_path=PurePosixPath("contracts/goals/OMN-20070.yaml"),
        contract_source_commit_sha="c" * 40,
        contract_sha256=_HASH_A,
        subject_commit_sha="d" * 40,
        subject_tree_sha="e" * 40,
        attempt_id=UUID("00000000-0000-4000-8000-000000000104"),
        attempt_sequence=3,
        running_attempt_store_revision=UUID("00000000-0000-4000-8000-000000000105"),
        running_attempt_snapshot_sha256=_HASH_A,
        execution_request_sha256=_HASH_B,
        result_sha256=_execution_result().content_sha256(),
        artifact_sha256=_execution_result().artifact_sha256,
        subject_manifest_sha256=_HASH_A,
        evaluation_observation_sha256=_HASH_B,
        verifier_artifact_sha256=_HASH_A,
        policy_revision=UUID("00000000-0000-4000-8000-000000000106"),
        execution_identity="github-actions/goal-verifier",
        started_at=started_at,
        completed_at=started_at + timedelta(seconds=90),
        signature="pending-signature",
    )


def test_execution_result_json_round_trip_preserves_canonical_bytes_and_digest() -> (
    None
):
    original = _execution_result()
    wire = original.model_dump_json()
    restored = ModelGoalExecutionResult.model_validate_json(wire)

    assert restored.model_dump_json() == wire
    assert restored.content_sha256() == original.content_sha256()
    assert restored.artifact_sha256 == tuple(sorted(original.artifact_sha256))


def test_signed_receipt_json_round_trip_preserves_semver_wire_and_signature() -> None:
    keypair = generate_keypair()
    unsigned = _execution_receipt()
    signed = unsigned.model_copy(
        update={
            "signature": sign_base64(
                keypair.private_key_bytes, unsigned.signing_payload()
            )
        }
    )
    wire = signed.model_dump_json()
    restored = ModelGoalSupervisorExecutionReceipt.model_validate_json(wire)

    assert restored.model_dump_json() == wire
    assert '"contract_schema_version":"1.0.0"' in wire
    assert restored.signing_payload() == signed.signing_payload()
    assert restored.content_sha256() == signed.content_sha256()
    assert verify_base64(
        keypair.public_key_bytes, restored.signing_payload(), restored.signature
    )
