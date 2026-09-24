# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Message, ack, status, friction, consent and epoch kinds, and the field
additions to the five original kinds (OMN-16177, typed work ledger task T2).

Covers the four acceptance criteria of task T2:

- AC1: a consent event whose ``out_of_scope`` is a placeholder (``none``,
  ``-`` and the rest of the ledger grammar's placeholder set), or whose
  ``approved_scope`` is empty, is refused.
- AC2: ``ModelWorkMessageSent`` has no consent-shaped field, so a message can
  never be read as consent (rule 18).
- AC3: ``ModelWorkResultRecorded`` records friction exactly one way: either
  ``friction_none`` or a non-empty ``friction_refs``, never both and never
  neither.
- AC4: a ``ModelSessionActor`` with no ``controller_id`` validates, and its
  ``actor_key`` is unchanged.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_cost_basis import EnumCostBasis
from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.enums.enum_work_outcome import EnumWorkOutcome
from omnibase_core.enums.governance.enum_pr_state import EnumPRState
from omnibase_core.models.events.work import (
    WORK_EVENT_PARTITION_KEY_FIELDS,
    ModelPrKey,
    ModelPrRef,
    ModelRecipients,
    ModelSessionActor,
    ModelWorkClaimReleased,
    ModelWorkClaimRequested,
    ModelWorkCorrectionRecorded,
    ModelWorkEventBase,
    ModelWorkFrictionRecorded,
    ModelWorkLedgerEpochOpened,
    ModelWorkMessageAcked,
    ModelWorkMessageSent,
    ModelWorkOperatorConsentRecorded,
    ModelWorkResultRecorded,
    ModelWorkRulingRecorded,
    ModelWorkStatusRecorded,
)
from omnibase_core.models.events.work.model_work_operator_consent_recorded import (
    CONSENT_APPROVERS,
    SCOPE_PLACEHOLDER_VALUES,
)

pytestmark = pytest.mark.unit

_EMITTED_AT = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
_CONTROLLER = uuid.UUID("e2583369-b006-4c23-9a79-b13061f0ea09")

# The rolling ledger row grammar's placeholder set (ledger_grammar.py
# PLACEHOLDER_VALUES in the workspace registry), copied here as data. Plan task T10 adds the
# cross-repo equality test; this one pins the core copy so a silent edit fails.
_GRAMMAR_PLACEHOLDERS = frozenset(
    {"", "-", "--", ".", "none", "n/a", "na", "nil", "tbd", "nothing", "?"}
)


def _actor(**overrides: object) -> ModelSessionActor:
    kwargs: dict[str, object] = {
        "session_handle": "typed-ledger-t2",
        "controller_id": _CONTROLLER,
        "agent_kind": "build-lane",
    }
    kwargs.update(overrides)
    return ModelSessionActor(**kwargs)  # type: ignore[arg-type]


def _base(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "event_id": uuid.uuid4(),
        "emitted_at": _EMITTED_AT,
        "actor": _actor(),
        "summary": "typed ledger task T2",
    }
    kwargs.update(overrides)
    return kwargs


def _consent(**overrides: object) -> ModelWorkOperatorConsentRecorded:
    kwargs = _base(
        operator_words="yes, all of the above",
        approved_scope=("omnibase_core typed ledger T2",),
        out_of_scope=("prod", "the .201 host"),
    )
    kwargs.update(overrides)
    return ModelWorkOperatorConsentRecorded(**kwargs)  # type: ignore[arg-type]


def _result(**overrides: object) -> ModelWorkResultRecorded:
    kwargs = _base(outcome=EnumWorkOutcome.LANDED, friction_none=True)
    kwargs.update(overrides)
    return ModelWorkResultRecorded(**kwargs)  # type: ignore[arg-type]


def _friction(**overrides: object) -> ModelWorkFrictionRecorded:
    kwargs = _base(
        ticket_id="OMN-16177",
        cost_lane_hours=Decimal("0.5"),
        cost_basis=EnumCostBasis.MEASURED,
    )
    kwargs.update(overrides)
    return ModelWorkFrictionRecorded(**kwargs)  # type: ignore[arg-type]


def _epoch(**overrides: object) -> ModelWorkLedgerEpochOpened:
    kwargs = _base(
        reason="roll",
        epoch_seq=1,
        archived_path="docs/tracking/archive/ROLLING_WORK_LEDGER_2026-09-24-split.md",
        archived_sha256="a" * 64,
        archived_line_count=3800,
    )
    kwargs.update(overrides)
    return ModelWorkLedgerEpochOpened(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AC1 — consent names what it approves and what it does not
# ---------------------------------------------------------------------------


def test_placeholder_set_matches_the_ledger_grammar() -> None:
    assert SCOPE_PLACEHOLDER_VALUES == _GRAMMAR_PLACEHOLDERS


@pytest.mark.parametrize("placeholder", sorted(_GRAMMAR_PLACEHOLDERS))
def test_consent_refuses_a_placeholder_out_of_scope(placeholder: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        _consent(out_of_scope=(placeholder,))
    assert "out_of_scope" in str(excinfo.value)


@pytest.mark.parametrize("placeholder", sorted(_GRAMMAR_PLACEHOLDERS))
def test_consent_refuses_a_placeholder_approved_scope(placeholder: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        _consent(approved_scope=(placeholder,))
    assert "approved_scope" in str(excinfo.value)


@pytest.mark.parametrize("spelling", ["None", " NONE ", "n/a.", "TBD", "-."])
def test_consent_placeholder_check_ignores_case_padding_and_a_trailing_dot(
    spelling: str,
) -> None:
    with pytest.raises(ValidationError):
        _consent(out_of_scope=(spelling,))


def test_consent_refuses_a_placeholder_among_real_entries() -> None:
    """One entry that names nothing is a list entry that bounds nothing."""
    with pytest.raises(ValidationError):
        _consent(out_of_scope=("prod", "none"))


@pytest.mark.parametrize("field", ["approved_scope", "out_of_scope"])
def test_consent_refuses_an_empty_scope_list(field: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        _consent(**{field: ()})
    assert field in str(excinfo.value)


@pytest.mark.parametrize("field", ["approved_scope", "out_of_scope"])
def test_consent_scope_fields_are_required(field: str) -> None:
    kwargs = _base(
        operator_words="go",
        approved_scope=("a",),
        out_of_scope=("b",),
    )
    del kwargs[field]
    with pytest.raises(ValidationError):
        ModelWorkOperatorConsentRecorded(**kwargs)  # type: ignore[arg-type]


def test_consent_requires_the_operator_words() -> None:
    with pytest.raises(ValidationError):
        _consent(operator_words="   ")


def test_consent_approver_is_the_rule_22_set_or_absent() -> None:
    assert frozenset({"operator", "jake"}) == CONSENT_APPROVERS
    assert _consent().approved_by is None
    assert _consent(approved_by="operator").approved_by == "operator"
    with pytest.raises(ValidationError):
        _consent(approved_by="some-lane")


def test_consent_round_trips() -> None:
    event = _consent(approved_by="operator")
    restored = ModelWorkOperatorConsentRecorded.model_validate_json(
        event.model_dump_json()
    )
    assert restored == event
    assert restored.kind is EnumWorkEventKind.CONSENT_RECORDED


# ---------------------------------------------------------------------------
# AC2 — a message can never be consent
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field", ["consent", "approved_by", "approved_scope", "out_of_scope"]
)
def test_message_has_no_consent_shaped_field(field: str) -> None:
    assert field not in ModelWorkMessageSent.model_fields
    assert field not in ModelWorkMessageAcked.model_fields


def test_message_refuses_a_smuggled_consent_field() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ModelWorkMessageSent(  # type: ignore[call-arg]
            **_base(to=ModelRecipients(operator=True)),  # type: ignore[arg-type]
            approved_scope=("everything",),
        )
    assert "extra_forbidden" in str(excinfo.value)


def test_message_names_recipients_and_optionally_what_it_answers() -> None:
    msg = ModelWorkMessageSent(
        **_base(to=ModelRecipients(lanes=frozenset({"runtime-train"})))  # type: ignore[arg-type]
    )
    assert msg.re is None
    reply = ModelWorkMessageSent(
        **_base(to=ModelRecipients(all_lanes=True), re=msg.event_id)  # type: ignore[arg-type]
    )
    assert reply.re == msg.event_id


def test_message_requires_recipients() -> None:
    with pytest.raises(ValidationError):
        ModelWorkMessageSent(**_base())  # type: ignore[arg-type]


def test_message_and_ack_cannot_answer_themselves() -> None:
    own = uuid.uuid4()
    with pytest.raises(ValidationError):
        ModelWorkMessageSent(
            **_base(event_id=own, to=ModelRecipients(operator=True), re=own)  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError):
        ModelWorkMessageAcked(**_base(event_id=own, re=own))  # type: ignore[arg-type]


def test_ack_requires_what_it_acknowledges() -> None:
    with pytest.raises(ValidationError):
        ModelWorkMessageAcked(**_base())  # type: ignore[arg-type]
    target = uuid.uuid4()
    assert ModelWorkMessageAcked(**_base(re=target)).re == target  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AC3 — a result records friction exactly one way
# ---------------------------------------------------------------------------


def test_result_with_friction_none_validates() -> None:
    assert _result().friction_none is True


def test_result_with_friction_refs_validates() -> None:
    ref = uuid.uuid4()
    event = _result(friction_none=False, friction_refs=frozenset({ref}))
    assert event.friction_refs == frozenset({ref})


def test_result_with_both_friction_spellings_is_refused() -> None:
    with pytest.raises(ValidationError) as excinfo:
        _result(friction_none=True, friction_refs=frozenset({uuid.uuid4()}))
    assert "friction" in str(excinfo.value)


def test_result_with_neither_friction_spelling_is_refused() -> None:
    with pytest.raises(ValidationError) as excinfo:
        _result(friction_none=False)
    assert "friction" in str(excinfo.value)


def test_result_closes_claims_and_dumps_its_sets_sorted() -> None:
    claims = [uuid.UUID(int=n) for n in (9, 3, 5)]
    event = _result(closes_claims=frozenset(claims))
    dumped = json.loads(event.model_dump_json())
    assert dumped["closes_claims"] == [str(c) for c in sorted(claims, key=str)]
    assert ModelWorkResultRecorded.model_validate_json(event.model_dump_json()) == event


# ---------------------------------------------------------------------------
# AC4 — controller_id is optional and actor_key does not move
# ---------------------------------------------------------------------------


def test_session_actor_without_controller_id_validates() -> None:
    actor = ModelSessionActor(session_handle="typed-ledger-t2", agent_kind="build-lane")
    assert actor.controller_id is None


def test_actor_key_does_not_depend_on_controller_id() -> None:
    with_controller = _actor()
    without_controller = _actor(controller_id=None)
    assert with_controller.actor_key == without_controller.actor_key
    assert without_controller.actor_key == "session:typed-ledger-t2"


def test_event_with_a_controllerless_actor_round_trips() -> None:
    event = _result(actor=_actor(controller_id=None))
    restored = ModelWorkResultRecorded.model_validate_json(event.model_dump_json())
    assert restored == event
    assert restored.actor_key == "session:typed-ledger-t2"


# ---------------------------------------------------------------------------
# Status and friction
# ---------------------------------------------------------------------------


def test_status_carries_pr_citations_and_a_countersign() -> None:
    target = uuid.uuid4()
    event = ModelWorkStatusRecorded(
        **_base(  # type: ignore[arg-type]
            pr_refs=(
                ModelPrRef(
                    repo="omnibase_core",
                    number=1747,
                    state=EnumPRState.MERGED,
                    merge_sha="0" * 40,
                ),
            ),
            countersigns=target,
            verdict="GREEN",
        )
    )
    assert event.countersigns == target
    restored = ModelWorkStatusRecorded.model_validate_json(event.model_dump_json())
    assert restored == event


def test_status_defaults_to_no_citations() -> None:
    event = ModelWorkStatusRecorded(**_base())  # type: ignore[arg-type]
    assert event.pr_refs == ()
    assert event.countersigns is None
    assert event.verdict is None


def test_status_cannot_countersign_itself() -> None:
    own = uuid.uuid4()
    with pytest.raises(ValidationError):
        ModelWorkStatusRecorded(**_base(event_id=own, countersigns=own))  # type: ignore[arg-type]


def test_friction_requires_an_omn_ticket() -> None:
    with pytest.raises(ValidationError):
        _friction(ticket_id=None)
    with pytest.raises(ValidationError):
        _friction(ticket_id="JIRA-12")
    with pytest.raises(ValidationError):
        _friction(ticket_id="OMN-")
    assert _friction().ticket_id == "OMN-16177"


def test_friction_cost_is_non_negative_and_carries_its_basis() -> None:
    with pytest.raises(ValidationError):
        _friction(cost_lane_hours=Decimal("-0.1"))
    with pytest.raises(ValidationError):
        _friction(cost_basis=None)
    zero = _friction(cost_lane_hours=Decimal(0), cost_basis=EnumCostBasis.ESTIMATED)
    assert zero.cost_lane_hours == Decimal(0)


def test_friction_round_trips_its_decimal_cost_exactly() -> None:
    event = _friction(cost_lane_hours=Decimal("0.25"))
    restored = ModelWorkFrictionRecorded.model_validate_json(event.model_dump_json())
    assert restored == event
    assert restored.cost_lane_hours == Decimal("0.25")


def test_cost_basis_values() -> None:
    assert {basis.value for basis in EnumCostBasis} == {"measured", "estimated"}


# ---------------------------------------------------------------------------
# Epoch
# ---------------------------------------------------------------------------


def test_roll_epoch_validates_without_a_review_list() -> None:
    event = _epoch(carried=(uuid.UUID(int=2), uuid.UUID(int=1)))
    assert event.review_list_ref is None
    restored = ModelWorkLedgerEpochOpened.model_validate_json(event.model_dump_json())
    assert restored == event


def test_cutover_epoch_requires_a_review_list() -> None:
    with pytest.raises(ValidationError) as excinfo:
        _epoch(reason="cutover", epoch_seq=0)
    assert "review_list_ref" in str(excinfo.value)
    event = _epoch(
        reason="cutover",
        epoch_seq=0,
        review_list_ref="beta/tracking/2026-09-24-cutover-review.md",
    )
    assert event.reason == "cutover"


@pytest.mark.parametrize(
    "overrides",
    [
        {"reason": "restart"},
        {"epoch_seq": -1},
        {"archived_sha256": "A" * 64},
        {"archived_sha256": "a" * 63},
        {"archived_line_count": -1},
        {"archived_path": "/abs/ROLLING_WORK_LEDGER.md"},
        {"archived_path": "docs/../../etc/ledger.md"},
        {"archived_path": ""},
        {"carried": (uuid.UUID(int=1), uuid.UUID(int=1))},
    ],
    ids=[
        "unknown-reason",
        "negative-seq",
        "uppercase-sha",
        "short-sha",
        "negative-line-count",
        "absolute-path",
        "escaping-path",
        "empty-path",
        "duplicate-carry",
    ],
)
def test_epoch_refuses_malformed_fields(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _epoch(**overrides)


# ---------------------------------------------------------------------------
# Changes to the five original kinds
# ---------------------------------------------------------------------------


def test_claim_requested_new_fields_default_and_round_trip() -> None:
    bare = ModelWorkClaimRequested(**_base(ticket_id="OMN-16177"))  # type: ignore[arg-type]
    assert bare.prs == frozenset()
    assert bare.scope_text is None
    assert bare.est_lane_hours is None
    assert bare.displaces is None
    assert bare.consent_ref is None

    full = ModelWorkClaimRequested(
        **_base(  # type: ignore[arg-type]
            ticket_id="OMN-16177",
            prs=frozenset(
                {
                    ModelPrKey(repo="omnibase_infra", number=4005),
                    ModelPrKey(repo="omnibase_core", number=1747),
                }
            ),
            scope_text="plan task T2",
            est_lane_hours=Decimal(3),
            displaces="task T3 start",
            consent_ref=uuid.uuid4(),
        )
    )
    dumped = json.loads(full.model_dump_json())
    assert [p["repo"] for p in dumped["prs"]] == ["omnibase_core", "omnibase_infra"]
    assert ModelWorkClaimRequested.model_validate_json(full.model_dump_json()) == full


def test_claim_requested_refuses_a_negative_estimate() -> None:
    with pytest.raises(ValidationError):
        ModelWorkClaimRequested(
            **_base(ticket_id="OMN-16177", est_lane_hours=Decimal(-1))  # type: ignore[arg-type]
        )


def test_claim_released_requires_the_claim_it_releases() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ModelWorkClaimReleased(**_base(ticket_id="OMN-16177"))  # type: ignore[arg-type]
    assert "claim_event_id" in str(excinfo.value)
    claim = uuid.uuid4()
    released = ModelWorkClaimReleased(
        **_base(ticket_id="OMN-16177", claim_event_id=claim)  # type: ignore[arg-type]
    )
    assert released.claim_event_id == claim


def test_ruling_requires_the_operator_words() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ModelWorkRulingRecorded(**_base())  # type: ignore[arg-type]
    assert "operator_words" in str(excinfo.value)
    with pytest.raises(ValidationError):
        ModelWorkRulingRecorded(**_base(operator_words=""))  # type: ignore[arg-type]
    ruling = ModelWorkRulingRecorded(
        **_base(  # type: ignore[arg-type]
            operator_words="stick with your recommendations",
            amends=uuid.uuid4(),
            supersedes=None,
        )
    )
    assert ruling.supersedes is None


def test_correction_names_what_it_corrects() -> None:
    bare = ModelWorkCorrectionRecorded(**_base())  # type: ignore[arg-type]
    assert bare.corrects is None
    assert bare.corrects_legacy_ts is None
    target = uuid.uuid4()
    typed = ModelWorkCorrectionRecorded(**_base(corrects=target))  # type: ignore[arg-type]
    assert typed.corrects == target
    legacy = ModelWorkCorrectionRecorded(
        **_base(corrects_legacy_ts="2026-09-23T17:58:19Z")  # type: ignore[arg-type]
    )
    assert legacy.corrects_legacy_ts == "2026-09-23T17:58:19Z"


# ---------------------------------------------------------------------------
# Kinds, partition keys and the shared base
# ---------------------------------------------------------------------------

_NEW_KINDS = {
    ModelWorkMessageSent: EnumWorkEventKind.MESSAGE_SENT,
    ModelWorkMessageAcked: EnumWorkEventKind.MESSAGE_ACKED,
    ModelWorkStatusRecorded: EnumWorkEventKind.STATUS_RECORDED,
    ModelWorkFrictionRecorded: EnumWorkEventKind.FRICTION_RECORDED,
    ModelWorkOperatorConsentRecorded: EnumWorkEventKind.CONSENT_RECORDED,
    ModelWorkLedgerEpochOpened: EnumWorkEventKind.LEDGER_EPOCH_OPENED,
}


def test_new_kind_values_are_the_plan_event_types() -> None:
    assert {kind.value for kind in _NEW_KINDS.values()} == {
        "work.message.sent",
        "work.message.acked",
        "work.status.recorded",
        "work.friction.recorded",
        "work.consent.recorded",
        "work.ledger.epoch.opened",
    }


@pytest.mark.parametrize("model", list(_NEW_KINDS), ids=lambda m: m.__name__)
def test_each_new_model_pins_its_kind_and_subclasses_the_base(
    model: type[ModelWorkEventBase],
) -> None:
    assert issubclass(model, ModelWorkEventBase)
    assert model.model_fields["kind"].default is _NEW_KINDS[model]
    assert model.model_config.get("frozen") is True
    assert model.model_config.get("extra") == "forbid"


@pytest.mark.parametrize("kind", list(_NEW_KINDS.values()), ids=str)
def test_new_kinds_partition_on_actor_key(kind: EnumWorkEventKind) -> None:
    assert WORK_EVENT_PARTITION_KEY_FIELDS[kind] == "actor_key"


def test_every_kind_declares_a_partition_key() -> None:
    assert set(WORK_EVENT_PARTITION_KEY_FIELDS) == set(EnumWorkEventKind)
