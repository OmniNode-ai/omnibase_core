# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Authenticated opening and revision source events for goal admission."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.crypto.crypto_ed25519_signer import generate_keypair
from omnibase_core.enums.enum_occ_eligibility_reason import EnumOccEligibilityReason
from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.envelope.model_message_envelope import ModelMessageEnvelope
from omnibase_core.models.events.work import (
    ModelSessionActor,
    ModelWorkClaimRequested,
    ModelWorkEvent,
    ModelWorkGoalRevised,
    ModelWorkRulingRecorded,
)
from omnibase_core.models.events.work.model_work_event_base import (
    WORK_EVENT_PARTITION_KEY_FIELDS,
)
from omnibase_core.models.events.work.model_work_goal_revision_resolution import (
    ModelWorkGoalRevisionResolution,
)
from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem
from omnibase_core.models.validation.model_goal_contract_revision_record import (
    ModelGoalContractRevisionRecord,
)
from omnibase_core.models.validation.model_goal_revision_authorization_policy import (
    ModelGoalRevisionAuthorizationPolicy,
)
from omnibase_core.models.validation.model_goal_revision_history_snapshot import (
    ModelGoalRevisionHistorySnapshot,
)
from tests.unit.validation.test_occ_merge_eligibility_goal_coverage_revision import (
    _WORK_ACTOR,
    _WORK_LEDGER_KEYPAIR,
    _WORK_LEDGER_RUNTIME_ID,
    _full_provider,
    _public_result,
)
from tests.unit.validation.test_occ_merge_eligibility_identity import (
    CONTRACT_REVISION,
    CONTRACT_SCHEMA_VERSION,
    GOAL_ID,
    REPOSITORY,
    _add_protected_test_source,
    _canonical_goal_sha256,
    _git,
    _goal_contract,
    _goal_repo,
)

pytestmark = pytest.mark.unit

_GOAL_PATH = "contracts/goals/example.yaml"
_POLICY_REVISION = UUID("00000000-0000-4000-8000-000000000451")
_ACTOR = _WORK_ACTOR
_EMITTED_AT = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
_WORK_LEDGER_TOPIC = "or2-work-ledger-source-event-tests"


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _write_goal_contract(repo_root: Path, contract: dict[str, object]) -> str:
    source = Path(__file__).parents[3]
    formatter = shutil.which("yamlfmt")
    assert formatter is not None
    path = repo_root / _GOAL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            contract, sort_keys=True, allow_unicode=True, explicit_start=True
        ),
        encoding="utf-8",
    )
    formatted = subprocess.run(
        [
            formatter,
            "-conf",
            str(source / ".yamlfmt"),
            "-no_global_conf",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert formatted.returncode == 0, formatted.stderr
    _git(repo_root, "add", _GOAL_PATH)
    _git(
        repo_root,
        "commit",
        "-m",
        f"publish goal revision {contract['contract_revision']}",
    )
    return _git(repo_root, "rev-parse", "HEAD")


def _source_chain_fixture(tmp_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create two immutable, formatted goal contract revisions in one repo."""
    initial_contract = _goal_contract(
        revision=GOAL_ID,
        description="The opening goal contract is complete and immutable.",
    )
    fixture = _goal_repo(tmp_path, contract=initial_contract)
    repo_root = fixture["repo_root"]
    assert isinstance(repo_root, Path)
    opening_commit = str(fixture["contract_source_commit"])
    opening_tree = str(fixture["contract_source_tree"])

    _add_protected_test_source(fixture)
    revised_contract = _goal_contract(
        revision=CONTRACT_REVISION,
        description="The appended replacement contract is complete and immutable.",
    )
    revision_commit = _write_goal_contract(repo_root, revised_contract)
    fixture.update(
        {
            "contract": revised_contract,
            "contract_source_commit": revision_commit,
            "contract_source_tree": _git(
                repo_root, "rev-parse", f"{revision_commit}^{{tree}}"
            ),
            "subject_commit": revision_commit,
            "subject_tree": _git(repo_root, "rev-parse", f"{revision_commit}^{{tree}}"),
        }
    )
    opening = {
        "contract": initial_contract,
        "source_commit": opening_commit,
        "source_tree": opening_tree,
    }
    revision = {
        "contract": revised_contract,
        "source_commit": revision_commit,
        "source_tree": fixture["contract_source_tree"],
    }
    return fixture, {"opening": opening, "revision": revision}


def _work_event(
    *,
    revision_id: UUID,
    parent_id: UUID | None,
    revision: dict[str, Any],
    actor: ModelSessionActor = _ACTOR,
    ticket_id: str | None = None,
) -> ModelWorkClaimRequested | ModelWorkGoalRevised:
    contract = revision["contract"]
    items = tuple(
        ModelContractDodItem.model_validate(item) for item in contract["dod_evidence"]
    )
    common = {
        "event_id": revision_id,
        "emitted_at": _EMITTED_AT,
        "actor": actor,
        "ticket_id": ticket_id,
        "summary": "record an immutable goal contract source event",
        "goal_id": GOAL_ID,
        "repository": REPOSITORY,
        "contract_source_commit_sha": revision["source_commit"],
        "contract_path": _GOAL_PATH,
        "contract_sha256": _canonical_goal_sha256(contract),
        "contract_schema_version": CONTRACT_SCHEMA_VERSION,
        "dod_evidence": items,
        "authorization_policy_revision": _POLICY_REVISION,
    }
    if parent_id is None:
        return ModelWorkClaimRequested.model_validate(
            {**common, "goal_id": revision_id}
        )
    return ModelWorkGoalRevised.model_validate(
        {**common, "replaces": parent_id, "reason": "Append a complete replacement."}
    )


def _signed_revision_record(
    *,
    revision_id: UUID,
    parent_id: UUID | None,
    revision: dict[str, Any],
    actor: ModelSessionActor = _ACTOR,
    runtime_id: str = _WORK_LEDGER_RUNTIME_ID,
    signing_key: bytes = _WORK_LEDGER_KEYPAIR.private_key_bytes,
    ticket_id: str | None = None,
) -> ModelGoalContractRevisionRecord:
    event = _work_event(
        revision_id=revision_id,
        parent_id=parent_id,
        revision=revision,
        actor=actor,
        ticket_id=ticket_id,
    )
    envelope = ModelMessageEnvelope[ModelWorkEvent].create_signed(
        realm="dev",
        runtime_id=runtime_id,
        bus_id=_WORK_LEDGER_TOPIC,
        payload=event,
        private_key=signing_key,
        emitted_at=event.emitted_at,
    )
    return ModelGoalContractRevisionRecord(
        goal_id=GOAL_ID,
        revision_id=revision_id,
        replaces_revision_id=parent_id,
        repository=REPOSITORY,
        contract_schema_version=CONTRACT_SCHEMA_VERSION,
        contract_path=_GOAL_PATH,
        contract_source_commit_sha=str(revision["source_commit"]),
        contract_sha256=_canonical_goal_sha256(revision["contract"]),
        dod_evidence=event.dod_evidence,
        authorization_policy_revision=_POLICY_REVISION,
        source_event=event,
        source_envelope=envelope,
    )


def _signed_history(
    records: tuple[ModelGoalContractRevisionRecord, ...],
    *,
    allowed_actor_keys: tuple[str, ...] = (_ACTOR.actor_key,),
    allowed_runtimes: tuple[str, ...] = (_WORK_LEDGER_RUNTIME_ID,),
) -> ModelGoalRevisionHistorySnapshot:
    policy_body = {
        "repository": REPOSITORY,
        "goal_id": str(GOAL_ID),
        "policy_revision": str(_POLICY_REVISION),
        "allowed_actor_keys": sorted(allowed_actor_keys),
        "allowed_event_runtime_ids": sorted(allowed_runtimes),
    }
    policy = ModelGoalRevisionAuthorizationPolicy(
        repository=REPOSITORY,
        goal_id=GOAL_ID,
        policy_revision=_POLICY_REVISION,
        allowed_actor_keys=allowed_actor_keys,
        allowed_event_runtime_ids=allowed_runtimes,
        policy_sha256=_sha256(
            json.dumps(policy_body, sort_keys=True, separators=(",", ":")).encode()
        ),
    )
    history = ModelGoalRevisionHistorySnapshot(
        repository=REPOSITORY,
        goal_id=GOAL_ID,
        store_revision=uuid4(),
        revisions=records,
        fork_resolutions=(),
        revision_authorization_policies=(policy,),
        snapshot_sha256=_sha256(b"pending"),
    )
    return history.model_copy(update={"snapshot_sha256": history.content_sha256()})


def _history_provider(
    fixture: dict[str, Any], history: ModelGoalRevisionHistorySnapshot
):
    provider = _full_provider(fixture, history=history)
    provider.ledger_key_provider.public_keys[_WORK_LEDGER_RUNTIME_ID] = (
        _WORK_LEDGER_KEYPAIR.public_key_bytes
    )
    return provider


@pytest.mark.unit
@pytest.mark.parametrize(
    ("opening_ticket_id", "revision_ticket_id"),
    [
        (None, None),
        ("OMN-20070", None),
        (None, "OMN-20070"),
        ("OMN-20070", "OMN-20070"),
    ],
)
def test_signed_opening_and_appended_revision_reach_final_policy_gate(
    tmp_path: Path,
    opening_ticket_id: str | None,
    revision_ticket_id: str | None,
) -> None:
    fixture, revisions = _source_chain_fixture(tmp_path)
    records = (
        _signed_revision_record(
            revision_id=GOAL_ID,
            parent_id=None,
            revision=revisions["opening"],
            ticket_id=opening_ticket_id,
        ),
        _signed_revision_record(
            revision_id=CONTRACT_REVISION,
            parent_id=GOAL_ID,
            revision=revisions["revision"],
            ticket_id=revision_ticket_id,
        ),
    )
    expected_goal_partition = f"goal:{REPOSITORY.lower()}:{GOAL_ID}"
    assert (
        WORK_EVENT_PARTITION_KEY_FIELDS[EnumWorkEventKind.CLAIM_REQUESTED]
        == "work_partition_key"
    )
    assert (
        WORK_EVENT_PARTITION_KEY_FIELDS[EnumWorkEventKind.GOAL_REVISED]
        == "work_partition_key"
    )
    assert all(
        record.source_event.work_partition_key == expected_goal_partition
        for record in records
    )
    history = _signed_history(records)
    provider = _history_provider(fixture, history)

    result = _public_result(fixture, provider)

    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE


@pytest.mark.unit
def test_ticket_correlation_does_not_change_explicit_goal_partition() -> None:
    contract = _goal_contract(revision=GOAL_ID)
    source = {
        "contract": contract,
        "source_commit": "a" * 40,
        "source_tree": "b" * 40,
    }
    event = _work_event(
        revision_id=GOAL_ID,
        parent_id=None,
        revision=source,
        ticket_id="OMN-20070",
    )

    assert event.ticket_id == "OMN-20070"
    assert (
        WORK_EVENT_PARTITION_KEY_FIELDS[EnumWorkEventKind.CLAIM_REQUESTED]
        == "work_partition_key"
    )
    assert event.work_partition_key == f"goal:{REPOSITORY.lower()}:{GOAL_ID}"


@pytest.mark.unit
@pytest.mark.parametrize(
    "missing_field",
    [
        "repository",
        "contract_source_commit_sha",
        "contract_path",
        "contract_sha256",
        "authorization_policy_revision",
    ],
)
def test_opening_goal_rejects_partial_source_tuple(
    tmp_path: Path, missing_field: str
) -> None:
    fixture, revisions = _source_chain_fixture(tmp_path)
    del fixture
    event = _work_event(
        revision_id=GOAL_ID,
        parent_id=None,
        revision=revisions["opening"],
        ticket_id="OMN-20070",
    )
    payload = event.model_dump(mode="json")
    payload[missing_field] = None
    if missing_field == "repository":
        payload["work_partition_key"] = payload["ticket_id"]

    with pytest.raises(ValidationError, match="every source and policy field"):
        ModelWorkClaimRequested.model_validate(payload)


@pytest.mark.unit
def test_ticket_cannot_turn_goal_id_without_source_tuple_into_legacy_claim() -> None:
    payload = {
        "event_id": GOAL_ID,
        "emitted_at": _EMITTED_AT,
        "actor": _ACTOR,
        "ticket_id": "OMN-20070",
        "goal_id": GOAL_ID,
        "summary": "partial goal claim must not fall back to ticket mode",
    }

    with pytest.raises(ValidationError, match="every source and policy field"):
        ModelWorkClaimRequested.model_validate(payload)


@pytest.mark.unit
@pytest.mark.parametrize(
    "missing_field",
    [
        "repository",
        "contract_source_commit_sha",
        "contract_path",
        "contract_sha256",
        "authorization_policy_revision",
    ],
)
def test_revision_rejects_partial_source_tuple(
    tmp_path: Path, missing_field: str
) -> None:
    _, revisions = _source_chain_fixture(tmp_path)
    event = _work_event(
        revision_id=CONTRACT_REVISION,
        parent_id=GOAL_ID,
        revision=revisions["revision"],
        ticket_id="OMN-20070",
    )
    payload = event.model_dump(mode="json")
    payload[missing_field] = None
    if missing_field == "repository":
        payload["work_partition_key"] = payload["ticket_id"]

    with pytest.raises(ValidationError, match="every source field"):
        ModelWorkGoalRevised.model_validate(payload)


@pytest.mark.unit
def test_historical_contract_bearing_revision_without_source_tuple_stays_ticketed() -> (
    None
):
    contract = _goal_contract(revision=GOAL_ID)
    event = ModelWorkGoalRevised.model_validate(
        {
            "event_id": CONTRACT_REVISION,
            "emitted_at": _EMITTED_AT,
            "actor": _ACTOR,
            "ticket_id": "OMN-20070",
            "goal_id": GOAL_ID,
            "summary": "preserve the historical ticketed revision event",
            "dod_evidence": tuple(
                ModelContractDodItem.model_validate(item)
                for item in contract["dod_evidence"]
            ),
            "contract_schema_version": CONTRACT_SCHEMA_VERSION,
            "reason": "preserve the historical ticketed revision wire form",
            "replaces": GOAL_ID,
        }
    )

    assert event.repository is None
    assert event.contract_source_commit_sha is None
    assert event.contract_path is None
    assert event.contract_sha256 is None
    assert event.authorization_policy_revision is None
    assert event.work_partition_key == "OMN-20070"


@pytest.mark.unit
@pytest.mark.parametrize("ticket_id", [None, "OMN-20070"])
def test_goal_revision_ruling_uses_same_goal_partition_with_optional_ticket(
    ticket_id: str | None,
) -> None:
    ruling = ModelWorkRulingRecorded(
        event_id=uuid4(),
        emitted_at=_EMITTED_AT,
        actor=_ACTOR,
        ticket_id=ticket_id,
        summary="authorize a complete revision history selection",
        operator_words="Select the named revision.",
        goal_revision_resolution=ModelWorkGoalRevisionResolution(
            goal_id=GOAL_ID,
            repository=REPOSITORY,
            fork_parent_revision_id=GOAL_ID,
            competing_revision_ids=(CONTRACT_REVISION, UUID(int=99)),
            selected_revision_id=CONTRACT_REVISION,
            resolution_policy_revision=_POLICY_REVISION,
        ),
    )

    partition_field = WORK_EVENT_PARTITION_KEY_FIELDS[EnumWorkEventKind.RULING_RECORDED]
    assert partition_field == "work_partition_key"
    assert getattr(ruling, partition_field) == f"goal:{REPOSITORY.lower()}:{GOAL_ID}"


@pytest.mark.unit
@pytest.mark.parametrize("bad_source", ["unknown-runtime", "unauthorized-actor"])
def test_signed_revision_source_requires_historical_actor_and_runtime_authority(
    tmp_path: Path, bad_source: str
) -> None:
    fixture, revisions = _source_chain_fixture(tmp_path)
    opening = _signed_revision_record(
        revision_id=GOAL_ID, parent_id=None, revision=revisions["opening"]
    )
    untrusted_runtime_key = generate_keypair()
    if bad_source == "unknown-runtime":
        record = _signed_revision_record(
            revision_id=CONTRACT_REVISION,
            parent_id=GOAL_ID,
            revision=revisions["revision"],
            runtime_id="runtime-unapproved-source",
            signing_key=untrusted_runtime_key.private_key_bytes,
        )
        allowed_runtimes = (_WORK_LEDGER_RUNTIME_ID,)
        expected = "goal opening/revision issuer is not authorized"
    else:
        intruder = ModelSessionActor(
            session_handle="goal-source-intruder", agent_kind="test"
        )
        record = _signed_revision_record(
            revision_id=CONTRACT_REVISION,
            parent_id=GOAL_ID,
            revision=revisions["revision"],
            actor=intruder,
        )
        allowed_runtimes = (_WORK_LEDGER_RUNTIME_ID,)
        expected = "goal opening/revision issuer is not authorized"
    provider = _history_provider(
        fixture,
        _signed_history((opening, record), allowed_runtimes=allowed_runtimes),
    )
    if bad_source == "unknown-runtime":
        provider.ledger_key_provider.public_keys[record.source_envelope.runtime_id] = (
            untrusted_runtime_key.public_key_bytes
        )

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID
    assert expected in result.detail


@pytest.mark.unit
def test_revised_source_record_rejects_mismatched_event_and_envelope(
    tmp_path: Path,
) -> None:
    _, revisions = _source_chain_fixture(tmp_path)
    opening = _signed_revision_record(
        revision_id=GOAL_ID, parent_id=None, revision=revisions["opening"]
    )
    revised = _signed_revision_record(
        revision_id=CONTRACT_REVISION,
        parent_id=GOAL_ID,
        revision=revisions["revision"],
    )
    altered_event = revised.source_event.model_copy(
        update={"summary": "edited after original signer approval"}
    )
    altered_envelope = revised.source_envelope.model_copy(
        update={"payload": altered_event}
    )
    altered_record = revised.model_copy(update={"source_envelope": altered_envelope})
    with pytest.raises(ValidationError, match="source event and signed envelope"):
        _signed_history((opening, altered_record))


@pytest.mark.unit
def test_source_envelope_with_unknown_key_fails_even_when_runtime_is_allowed(
    tmp_path: Path,
) -> None:
    fixture, revisions = _source_chain_fixture(tmp_path)
    opening = _signed_revision_record(
        revision_id=GOAL_ID, parent_id=None, revision=revisions["opening"]
    )
    untrusted_key_record = _signed_revision_record(
        revision_id=CONTRACT_REVISION,
        parent_id=GOAL_ID,
        revision=revisions["revision"],
        signing_key=generate_keypair().private_key_bytes,
    )
    provider = _history_provider(
        fixture, _signed_history((opening, untrusted_key_record))
    )

    result = _public_result(fixture, provider)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.GOAL_REVISION_HISTORY_INVALID
    assert "authentic signed Work Ledger envelope" in result.detail
