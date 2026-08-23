# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Work-event schema tests (OMN-16177).

Covers the falsifiable acceptance items 3-7 of OMN-16177: frozen/extra-forbid
models, a ``ModelQuantClaim`` that cannot carry a number without the command
that produced it, an ``emitted_at`` with no wall-clock default, an actor union
that round-trips both variants without coercion, and the per-kind partition-key
contract the emit registry must match.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_actor_kind import EnumActorKind
from omnibase_core.enums.enum_proof_class import EnumProofClass
from omnibase_core.enums.enum_runtime_lane import EnumRuntimeLane
from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.enums.enum_work_outcome import EnumWorkOutcome
from omnibase_core.enums.governance.enum_pr_state import EnumPRState
from omnibase_core.models.events.work import (
    WORK_EVENT_PARTITION_KEY_FIELDS,
    ModelNodeActor,
    ModelPrRef,
    ModelQuantClaim,
    ModelSessionActor,
    ModelWorkClaimReleased,
    ModelWorkClaimRequested,
    ModelWorkCorrectionRecorded,
    ModelWorkEventBase,
    ModelWorkResultRecorded,
    ModelWorkRulingRecorded,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

pytestmark = pytest.mark.unit

_EMITTED_AT = datetime(2026, 8, 18, 14, 30, tzinfo=UTC)


def _session_actor() -> ModelSessionActor:
    return ModelSessionActor(
        session_handle="omn16177-build-1",
        controller_id=uuid.UUID("e2583369-b006-4c23-9a79-b13061f0ea09"),
        agent_kind="build-lane",
    )


def _node_actor() -> ModelNodeActor:
    return ModelNodeActor(
        node_id="node_pr_lifecycle_orchestrator",
        runtime_lane=EnumRuntimeLane.STABILITY_TEST,
        contract_version=ModelSemVer(major=1, minor=4, patch=0),
        run_id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
    )


def _ruling(**overrides: object) -> ModelWorkRulingRecorded:
    kwargs: dict[str, object] = {
        "event_id": uuid.uuid4(),
        "emitted_at": _EMITTED_AT,
        "actor": _session_actor(),
        "ticket_id": "OMN-16177",
        "summary": "operator ruling recorded",
    }
    kwargs.update(overrides)
    return ModelWorkRulingRecorded(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Acceptance 3 — frozen, extra="forbid"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory",
    [
        _session_actor,
        _node_actor,
        lambda: ModelPrRef(
            repo="omnibase_core",
            number=1559,
            state=EnumPRState.MERGED,
            merge_sha="d" * 40,
        ),
        lambda: ModelQuantClaim(
            value="214925",
            unit="rows",
            probe_command="psql -c 'SELECT count(*) FROM event_ledger'",
            observed_at=_EMITTED_AT,
        ),
        _ruling,
    ],
    ids=["session_actor", "node_actor", "pr_ref", "quant_claim", "work_event"],
)
def test_models_are_frozen(factory: object) -> None:
    """Every work-event model rejects mutation after construction."""
    instance = factory()  # type: ignore[operator]
    field_name = next(iter(type(instance).model_fields))
    with pytest.raises(ValidationError):
        setattr(instance, field_name, "mutated")


def test_unknown_field_is_rejected() -> None:
    """extra="forbid" — an unknown key is a hard ValidationError, never ignored."""
    with pytest.raises(ValidationError) as excinfo:
        _ruling(unexpected_field="smuggled")
    assert "extra_forbidden" in str(excinfo.value)


def test_unknown_field_is_rejected_on_actor() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ModelSessionActor(
            session_handle="h",
            controller_id=uuid.uuid4(),
            agent_kind="k",
            node_id="node_smuggled_in",  # type: ignore[call-arg]
        )
    assert "extra_forbidden" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Acceptance 4 — a number cannot be emitted without the command that produced it
# ---------------------------------------------------------------------------


def test_quant_claim_requires_probe_command() -> None:
    """OMN-15897's write-time lint becomes a structural requirement."""
    with pytest.raises(ValidationError) as excinfo:
        ModelQuantClaim(  # type: ignore[call-arg]
            value="214925",
            unit="rows",
            observed_at=_EMITTED_AT,
        )
    assert "probe_command" in str(excinfo.value)


def test_quant_claim_rejects_blank_probe_command() -> None:
    """An empty string is not a probe — whitespace must not satisfy the field."""
    with pytest.raises(ValidationError):
        ModelQuantClaim(
            value="214925",
            unit="rows",
            probe_command="   ",
            observed_at=_EMITTED_AT,
        )


def test_quant_claim_requires_observed_at() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ModelQuantClaim(  # type: ignore[call-arg]
            value="214925",
            unit="rows",
            probe_command="wc -l file",
        )
    assert "observed_at" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Acceptance 5 — emitted_at is emitter-assigned, never wall-clock-defaulted
# ---------------------------------------------------------------------------


def test_emitted_at_has_no_default() -> None:
    """Construction without emitted_at raises rather than silently stamping now()."""
    with pytest.raises(ValidationError) as excinfo:
        ModelWorkRulingRecorded(  # type: ignore[call-arg]
            event_id=uuid.uuid4(),
            actor=_session_actor(),
            ticket_id="OMN-16177",
            summary="no timestamp supplied",
        )
    assert "emitted_at" in str(excinfo.value)


def test_emitted_at_field_declares_no_wall_clock_default() -> None:
    """Guards the regression directly: no default and no default_factory."""
    field = ModelWorkEventBase.model_fields["emitted_at"]
    assert field.is_required()
    assert field.default_factory is None


def test_event_id_has_no_default() -> None:
    """The idempotency key is emitter-assigned too — no uuid4 default_factory."""
    field = ModelWorkEventBase.model_fields["event_id"]
    assert field.is_required()
    assert field.default_factory is None


def test_emitted_at_requires_timezone() -> None:
    """A naive datetime is not a point in time across lanes."""
    with pytest.raises(ValidationError):
        _ruling(emitted_at=datetime(2026, 8, 18, 14, 30))


# ---------------------------------------------------------------------------
# Acceptance 6 — the actor union round-trips both variants, no coercion
# ---------------------------------------------------------------------------


def test_session_actor_round_trips_with_discriminator() -> None:
    original = _ruling(actor=_session_actor())
    restored = ModelWorkRulingRecorded.model_validate_json(original.model_dump_json())
    assert isinstance(restored.actor, ModelSessionActor)
    assert restored.actor.kind is EnumActorKind.SESSION
    assert restored == original


def test_node_actor_round_trips_with_discriminator() -> None:
    original = _ruling(actor=_node_actor())
    restored = ModelWorkRulingRecorded.model_validate_json(original.model_dump_json())
    assert isinstance(restored.actor, ModelNodeActor)
    assert restored.actor.kind is EnumActorKind.NODE
    assert restored.actor.runtime_lane is EnumRuntimeLane.STABILITY_TEST
    assert restored == original


def test_node_actor_is_not_coerced_into_session_actor() -> None:
    """The failure this test exists to catch: a node claim read as a session claim."""
    payload = _ruling(actor=_node_actor()).model_dump(mode="json")
    restored = ModelWorkRulingRecorded.model_validate(payload)
    assert not isinstance(restored.actor, ModelSessionActor)
    assert isinstance(restored.actor, ModelNodeActor)


def test_actor_without_discriminator_is_rejected() -> None:
    payload = _ruling(actor=_node_actor()).model_dump(mode="json")
    del payload["actor"]["kind"]
    with pytest.raises(ValidationError) as excinfo:
        ModelWorkRulingRecorded.model_validate(payload)
    assert "kind" in str(excinfo.value)


def test_node_actor_fields_are_rejected_on_a_session_discriminator() -> None:
    """Mislabelling a node actor as a session actor fails; it does not half-parse."""
    payload = _ruling(actor=_node_actor()).model_dump(mode="json")
    payload["actor"]["kind"] = EnumActorKind.SESSION.value
    with pytest.raises(ValidationError):
        ModelWorkRulingRecorded.model_validate(payload)


def test_runtime_lane_rejects_an_unknown_lane() -> None:
    """runtime_lane is load-bearing for claim arbitration — it is a closed set."""
    with pytest.raises(ValidationError):
        ModelNodeActor(
            node_id="node_pr_lifecycle_orchestrator",
            runtime_lane="not-a-lane",  # type: ignore[arg-type]
            contract_version=ModelSemVer(major=1, minor=4, patch=0),
            run_id=uuid.uuid4(),
        )


# ---------------------------------------------------------------------------
# actor_key — the flat partition key the transport requires
# ---------------------------------------------------------------------------


def test_actor_key_is_derived_for_a_session_actor() -> None:
    event = _ruling(actor=_session_actor())
    assert event.actor_key == "session:omn16177-build-1"


def test_actor_key_carries_the_runtime_lane_for_a_node_actor() -> None:
    """Two lanes running the same node must not share a narrative partition key."""
    dev = _node_actor().model_copy(update={"runtime_lane": EnumRuntimeLane.DEV})
    stability = _node_actor()
    assert _ruling(actor=dev).actor_key != _ruling(actor=stability).actor_key
    assert (
        _ruling(actor=stability).actor_key
        == "node:node_pr_lifecycle_orchestrator@stability-test"
    )


def test_actor_key_survives_round_trip() -> None:
    original = _ruling(actor=_node_actor())
    restored = ModelWorkRulingRecorded.model_validate_json(original.model_dump_json())
    assert restored.actor_key == original.actor_key


def test_actor_key_inconsistent_with_actor_is_rejected() -> None:
    """A hand-forged partition key must not silently override the actor it names."""
    payload = _ruling(actor=_node_actor()).model_dump(mode="json")
    payload["actor_key"] = "session:someone-else"
    with pytest.raises(ValidationError) as excinfo:
        ModelWorkRulingRecorded.model_validate(payload)
    assert "actor_key" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Acceptance 7 — the two partition-key domains
# ---------------------------------------------------------------------------


def test_claim_kinds_partition_on_ticket_id() -> None:
    for kind in (
        EnumWorkEventKind.CLAIM_REQUESTED,
        EnumWorkEventKind.CLAIM_RELEASED,
    ):
        assert WORK_EVENT_PARTITION_KEY_FIELDS[kind] == "ticket_id"


def test_narrative_kinds_partition_on_actor_identity() -> None:
    for kind in (
        EnumWorkEventKind.RESULT_RECORDED,
        EnumWorkEventKind.RULING_RECORDED,
        EnumWorkEventKind.CORRECTION_RECORDED,
    ):
        assert WORK_EVENT_PARTITION_KEY_FIELDS[kind] == "actor_key"


def test_every_kind_declares_a_partition_key() -> None:
    assert set(WORK_EVENT_PARTITION_KEY_FIELDS) == set(EnumWorkEventKind)


def test_partition_key_fields_are_flat_payload_keys() -> None:
    """The emit registry does a flat payload.get() — a dotted path would key on None."""
    for field_name in WORK_EVENT_PARTITION_KEY_FIELDS.values():
        assert "." not in field_name
        assert field_name in ModelWorkEventBase.model_fields


# ---------------------------------------------------------------------------
# Claim kinds require the ticket they arbitrate
# ---------------------------------------------------------------------------


def test_claim_requested_requires_a_ticket_id() -> None:
    """ticket_id is the claim partition key; a null key cannot arbitrate."""
    with pytest.raises(ValidationError) as excinfo:
        ModelWorkClaimRequested(  # type: ignore[call-arg]
            event_id=uuid.uuid4(),
            emitted_at=_EMITTED_AT,
            actor=_session_actor(),
            ticket_id=None,
            summary="claiming nothing in particular",
        )
    assert "ticket_id" in str(excinfo.value)


def test_claim_released_requires_a_ticket_id() -> None:
    with pytest.raises(ValidationError):
        ModelWorkClaimReleased(  # type: ignore[call-arg]
            event_id=uuid.uuid4(),
            emitted_at=_EMITTED_AT,
            actor=_node_actor(),
            ticket_id=None,
            summary="releasing nothing in particular",
        )


def test_narrative_kinds_allow_an_absent_ticket_id() -> None:
    event = _ruling(ticket_id=None)
    assert event.ticket_id is None


# ---------------------------------------------------------------------------
# Kind discriminator + structured citations
# ---------------------------------------------------------------------------


def test_each_model_pins_its_kind() -> None:
    expected = {
        ModelWorkClaimRequested: EnumWorkEventKind.CLAIM_REQUESTED,
        ModelWorkClaimReleased: EnumWorkEventKind.CLAIM_RELEASED,
        ModelWorkResultRecorded: EnumWorkEventKind.RESULT_RECORDED,
        ModelWorkRulingRecorded: EnumWorkEventKind.RULING_RECORDED,
        ModelWorkCorrectionRecorded: EnumWorkEventKind.CORRECTION_RECORDED,
    }
    for model, kind in expected.items():
        assert model.model_fields["kind"].default is kind


def test_kind_cannot_be_overridden() -> None:
    with pytest.raises(ValidationError):
        _ruling(kind=EnumWorkEventKind.RESULT_RECORDED)


def test_result_recorded_carries_structured_citations() -> None:
    event = ModelWorkResultRecorded(
        event_id=uuid.uuid4(),
        emitted_at=_EMITTED_AT,
        actor=_session_actor(),
        ticket_id="OMN-16177",
        summary="schema increment landed",
        proof_class=EnumProofClass.CODE_ONLY,
        outcome=EnumWorkOutcome.LANDED,
        pr_refs=[
            ModelPrRef(
                repo="omnibase_core",
                number=1560,
                state=EnumPRState.MERGED,
                merge_sha="a" * 40,
            )
        ],
        quantitative_claims=[
            ModelQuantClaim(
                value="26",
                unit="topics",
                probe_command="SELECT DISTINCT topic FROM event_ledger",
                observed_at=_EMITTED_AT,
            )
        ],
    )
    assert event.pr_refs[0].number == 1560
    assert event.occ_refs == ()
    restored = ModelWorkResultRecorded.model_validate_json(event.model_dump_json())
    assert restored == event


def test_result_recorded_defaults_to_no_citations_not_none() -> None:
    event = ModelWorkResultRecorded(
        event_id=uuid.uuid4(),
        emitted_at=_EMITTED_AT,
        actor=_node_actor(),
        ticket_id="OMN-16177",
        summary="blocked on a circular gate",
        outcome=EnumWorkOutcome.BLOCKED,
    )
    assert event.pr_refs == ()
    assert event.occ_refs == ()
    assert event.quantitative_claims == ()
    assert event.proof_class is None


def test_pr_ref_rejects_a_non_positive_number() -> None:
    with pytest.raises(ValidationError):
        ModelPrRef(repo="omnibase_core", number=0, state=EnumPRState.OPEN)


def test_pr_ref_rejects_a_malformed_merge_sha() -> None:
    with pytest.raises(ValidationError):
        ModelPrRef(
            repo="omnibase_core",
            number=1560,
            state=EnumPRState.MERGED,
            merge_sha="not-a-sha",
        )


def test_merged_pr_ref_requires_a_merge_sha() -> None:
    """A merged citation without its merge commit is an unverifiable claim."""
    with pytest.raises(ValidationError) as excinfo:
        ModelPrRef(repo="omnibase_core", number=1560, state=EnumPRState.MERGED)
    assert "merge_sha" in str(excinfo.value)


def test_open_pr_ref_must_not_carry_a_merge_sha() -> None:
    with pytest.raises(ValidationError):
        ModelPrRef(
            repo="omnibase_core",
            number=1560,
            state=EnumPRState.OPEN,
            merge_sha="a" * 40,
        )


# ---------------------------------------------------------------------------
# summary bound
# ---------------------------------------------------------------------------


def test_summary_is_bounded() -> None:
    with pytest.raises(ValidationError):
        _ruling(summary="x" * 2001)


def test_summary_accepts_the_boundary_length() -> None:
    assert len(_ruling(summary="x" * 2000).summary) == 2000


def test_summary_rejects_blank() -> None:
    with pytest.raises(ValidationError):
        _ruling(summary="   ")


# ---------------------------------------------------------------------------
# event kind values match the registry event_type strings
# ---------------------------------------------------------------------------


def test_event_kind_values_are_the_registry_event_types() -> None:
    assert {kind.value for kind in EnumWorkEventKind} == {
        "work.claim.requested",
        "work.claim.released",
        "work.result.recorded",
        "work.ruling.recorded",
        "work.correction.recorded",
    }


def test_work_outcome_values() -> None:
    assert {outcome.value for outcome in EnumWorkOutcome} == {
        "landed",
        "blocked",
        "abandoned",
        "superseded",
        "terminal",
    }
