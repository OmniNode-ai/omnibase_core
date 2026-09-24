# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The work-event union, the ledger record and the canonical JSON line
(OMN-16177, typed work ledger task T3).

Covers the three acceptance criteria of task T3:

- AC1: for each of the 13 kinds, ``parse(dump(x)) == x`` and
  ``dump(parse(dump(x))) == dump(x)`` byte for byte, by one fixture per kind
  and by a Hypothesis round trip.
- AC2: an unknown ``schema``, an unknown ``kind``, an extra field, a naive
  timestamp and a trailing-garbage line each raise ``WorkLedgerParseError``.
- AC3: ``events_path_from_env()`` returns
  ``Path(os.environ["ONEX_WORK_LEDGER_PATH"])`` and raises ``KeyError`` naming
  the variable when it is unset.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import get_args

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from omnibase_core.enums.enum_cost_basis import EnumCostBasis
from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.enums.enum_runtime_lane import EnumRuntimeLane
from omnibase_core.enums.enum_surface_result import EnumSurfaceResult
from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.enums.enum_work_outcome import EnumWorkOutcome
from omnibase_core.enums.governance.enum_pr_state import EnumPRState
from omnibase_core.errors.error_work_ledger_parse import WorkLedgerParseError
from omnibase_core.models.events.work import (
    WORK_LEDGER_EVENTS_PATH_ENV,
    WORK_LEDGER_SCHEMA,
    ModelHoldScope,
    ModelNodeActor,
    ModelPrKey,
    ModelPrRef,
    ModelQuantClaim,
    ModelRecipients,
    ModelSessionActor,
    ModelWorkClaimReleased,
    ModelWorkClaimRequested,
    ModelWorkCorrectionRecorded,
    ModelWorkEvent,
    ModelWorkEventBase,
    ModelWorkFrictionRecorded,
    ModelWorkHoldPlaced,
    ModelWorkHoldReleased,
    ModelWorkLedgerEpochOpened,
    ModelWorkLedgerRecord,
    ModelWorkMessageAcked,
    ModelWorkMessageSent,
    ModelWorkOperatorConsentRecorded,
    ModelWorkResultRecorded,
    ModelWorkRulingRecorded,
    ModelWorkStatusRecorded,
    dump_work_ledger_line,
    events_path_from_env,
    parse_work_ledger_line,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

pytestmark = pytest.mark.unit

_EMITTED_AT = datetime(2026, 9, 24, 13, 30, 5, 123456, tzinfo=UTC)
_REF_A = uuid.UUID("11111111-1111-4111-8111-111111111111")
_REF_B = uuid.UUID("22222222-2222-4222-8222-222222222222")


def _session() -> ModelSessionActor:
    return ModelSessionActor(session_handle="typed-ledger-t3", agent_kind="build-lane")


def _node() -> ModelNodeActor:
    return ModelNodeActor(
        node_id="node_pr_lifecycle_orchestrator",
        runtime_lane=EnumRuntimeLane.DEV,
        contract_version=ModelSemVer(major=1, minor=2, patch=3),
        run_id=uuid.UUID("33333333-3333-4333-8333-333333333333"),
    )


def _base(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "event_id": uuid.UUID("44444444-4444-4444-8444-444444444444"),
        "emitted_at": _EMITTED_AT,
        "actor": _session(),
        "ticket_id": "OMN-16177",
        "summary": "typed ledger task T3",
    }
    kwargs.update(overrides)
    return kwargs


def _claim_requested() -> ModelWorkEventBase:
    return ModelWorkClaimRequested(
        **_base(  # type: ignore[arg-type]  # NOTE(OMN-16177): kwargs dict built by _base
            prs=frozenset(
                {
                    ModelPrKey(repo="omnibase_infra", number=4005),
                    ModelPrKey(repo="omnibase_core", number=1752),
                }
            ),
            scope_text="plan T3",
            est_lane_hours=Decimal("2.5"),
            displaces="typed-ledger T4 start",
            consent_ref=_REF_A,
        )
    )


def _claim_released() -> ModelWorkEventBase:
    return ModelWorkClaimReleased(**_base(claim_event_id=_REF_A))  # type: ignore[arg-type]  # NOTE(OMN-16177): kwargs dict built by _base


def _result() -> ModelWorkEventBase:
    return ModelWorkResultRecorded(
        **_base(  # type: ignore[arg-type]  # NOTE(OMN-16177): kwargs dict built by _base
            actor=_node(),
            outcome=EnumWorkOutcome.LANDED,
            pr_refs=(
                ModelPrRef(
                    repo="omnibase_core",
                    number=1752,
                    state=EnumPRState.MERGED,
                    merge_sha="ab" * 20,
                ),
            ),
            quantitative_claims=(
                ModelQuantClaim(
                    value="157",
                    unit="tests passed",
                    probe_command="uv run pytest tests/unit/models/events/work -q",
                    observed_at=datetime(
                        2026, 9, 24, 15, 0, tzinfo=timezone(timedelta(hours=2))
                    ),
                ),
            ),
            closes_claims=frozenset({_REF_B, _REF_A}),
            friction_refs=frozenset({_REF_A}),
        )
    )


def _ruling() -> ModelWorkEventBase:
    return ModelWorkRulingRecorded(
        **_base(  # type: ignore[arg-type]  # NOTE(OMN-16177): kwargs dict built by _base
            operator_words="stick with your recommendations",
            amends=_REF_A,
        )
    )


def _correction() -> ModelWorkEventBase:
    return ModelWorkCorrectionRecorded(
        **_base(corrects_legacy_ts="2026-09-23T14:27:35Z")  # type: ignore[arg-type]  # NOTE(OMN-16177): kwargs dict built by _base
    )


def _hold_placed() -> ModelWorkEventBase:
    return ModelWorkHoldPlaced(
        **_base(  # type: ignore[arg-type]  # NOTE(OMN-16177): kwargs dict built by _base
            scope=ModelHoldScope(
                prs=frozenset({ModelPrKey(repo="omnibase_infra", number=4013)}),
                repos=frozenset({"omnimarket", "omnibase_infra"}),
                surfaces=frozenset({"dogfood-105"}),
                lanes=frozenset({"runtime-train", "merge-drain-7f"}),
            ),
            blocks=frozenset({EnumHoldBlock.MERGE, EnumHoldBlock.ARM}),
            runtime_only=True,
            addressed_to=ModelRecipients(
                lanes=frozenset({"b-lane", "a-lane"}), operator=True
            ),
            expires_at=datetime(2026, 9, 24, 18, 0, tzinfo=UTC),
            until_text="until the cut",
        )
    )


def _hold_released() -> ModelWorkEventBase:
    return ModelWorkHoldReleased(
        **_base(  # type: ignore[arg-type]  # NOTE(OMN-16177): kwargs dict built by _base
            releases=_REF_A,
            reap=True,
            surface_result=EnumSurfaceResult.PASS,
            surface_restored=True,
        )
    )


def _message_sent() -> ModelWorkEventBase:
    return ModelWorkMessageSent(
        **_base(to=ModelRecipients(all_lanes=True), re=_REF_B)  # type: ignore[arg-type]  # NOTE(OMN-16177): kwargs dict built by _base
    )


def _message_acked() -> ModelWorkEventBase:
    return ModelWorkMessageAcked(**_base(re=_REF_B))  # type: ignore[arg-type]  # NOTE(OMN-16177): kwargs dict built by _base


def _status() -> ModelWorkEventBase:
    return ModelWorkStatusRecorded(
        **_base(  # type: ignore[arg-type]  # NOTE(OMN-16177): kwargs dict built by _base
            pr_refs=(
                ModelPrRef(repo="omnibase_core", number=1753, state=EnumPRState.OPEN),
            ),
            countersigns=_REF_A,
            verdict="green on the exact head",
        )
    )


def _friction() -> ModelWorkEventBase:
    return ModelWorkFrictionRecorded(
        **_base(  # type: ignore[arg-type]  # NOTE(OMN-16177): kwargs dict built by _base
            cost_lane_hours=Decimal("0.10"),
            cost_basis=EnumCostBasis.ESTIMATED,
        )
    )


def _consent() -> ModelWorkEventBase:
    return ModelWorkOperatorConsentRecorded(
        **_base(  # type: ignore[arg-type]  # NOTE(OMN-16177): kwargs dict built by _base
            operator_words="yes, go",
            approved_by="operator",
            approved_scope=("omnibase_core typed ledger T3",),
            out_of_scope=("prod", "the .201 host"),
        )
    )


def _epoch() -> ModelWorkEventBase:
    return ModelWorkLedgerEpochOpened(
        **_base(  # type: ignore[arg-type]  # NOTE(OMN-16177): kwargs dict built by _base
            reason="cutover",
            epoch_seq=0,
            archived_path="docs/tracking/archive/ROLLING_WORK_LEDGER_PRE_TYPED.md",
            archived_sha256="b" * 64,
            archived_line_count=3800,
            carried=(_REF_B, _REF_A),
            review_list_ref="beta/tracking/typed-ledger-cutover-review.md",
        )
    )


_FIXTURES: dict[EnumWorkEventKind, Callable[[], ModelWorkEventBase]] = {
    EnumWorkEventKind.CLAIM_REQUESTED: _claim_requested,
    EnumWorkEventKind.CLAIM_RELEASED: _claim_released,
    EnumWorkEventKind.RESULT_RECORDED: _result,
    EnumWorkEventKind.RULING_RECORDED: _ruling,
    EnumWorkEventKind.CORRECTION_RECORDED: _correction,
    EnumWorkEventKind.HOLD_PLACED: _hold_placed,
    EnumWorkEventKind.HOLD_RELEASED: _hold_released,
    EnumWorkEventKind.MESSAGE_SENT: _message_sent,
    EnumWorkEventKind.MESSAGE_ACKED: _message_acked,
    EnumWorkEventKind.STATUS_RECORDED: _status,
    EnumWorkEventKind.FRICTION_RECORDED: _friction,
    EnumWorkEventKind.CONSENT_RECORDED: _consent,
    EnumWorkEventKind.LEDGER_EPOCH_OPENED: _epoch,
}


def _record(event: ModelWorkEventBase) -> ModelWorkLedgerRecord:
    return ModelWorkLedgerRecord(schema=WORK_LEDGER_SCHEMA, event=event)  # type: ignore[arg-type]  # NOTE(OMN-16177): fixtures return the base type; the union validates the concrete kind


# ---------------------------------------------------------------------------
# The union covers exactly the 13 kinds
# ---------------------------------------------------------------------------


def test_fixture_per_kind_covers_every_kind() -> None:
    assert set(_FIXTURES) == set(EnumWorkEventKind)
    assert len(_FIXTURES) == 13
    for kind, build in _FIXTURES.items():
        assert build().kind == kind


def test_union_members_are_the_thirteen_kind_models() -> None:
    union_args = get_args(get_args(ModelWorkEvent)[0])
    members = {model.model_fields["kind"].default for model in union_args}
    assert members == set(EnumWorkEventKind)
    assert len(union_args) == 13


def test_record_discriminates_to_the_concrete_kind() -> None:
    for kind, build in _FIXTURES.items():
        event = build()
        parsed = parse_work_ledger_line(dump_work_ledger_line(_record(event)))
        assert type(parsed.event) is type(event), kind


# ---------------------------------------------------------------------------
# AC1 — round trip, and the dump is byte-deterministic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", sorted(EnumWorkEventKind))
def test_round_trip_per_kind(kind: EnumWorkEventKind) -> None:
    record = _record(_FIXTURES[kind]())
    line = dump_work_ledger_line(record)
    parsed = parse_work_ledger_line(line)
    assert parsed == record
    assert dump_work_ledger_line(parsed) == line


@pytest.mark.parametrize("kind", sorted(EnumWorkEventKind))
def test_dump_is_canonical_json(kind: EnumWorkEventKind) -> None:
    line = dump_work_ledger_line(_record(_FIXTURES[kind]()))
    assert "\n" not in line
    assert "\r" not in line
    assert line.isascii()
    obj = json.loads(line)
    assert line == json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    assert obj["schema"] == WORK_LEDGER_SCHEMA
    assert obj["event"]["kind"] == kind.value


def test_timestamps_are_written_in_utc_with_z() -> None:
    record = _record(_FIXTURES[EnumWorkEventKind.RESULT_RECORDED]())
    obj = json.loads(dump_work_ledger_line(record))
    assert obj["event"]["emitted_at"] == "2026-09-24T13:30:05.123456Z"
    # 15:00 at +02:00 is written as 13:00Z; the instant is unchanged.
    assert (
        obj["event"]["quantitative_claims"][0]["observed_at"] == "2026-09-24T13:00:00Z"
    )


def test_set_valued_fields_are_written_sorted() -> None:
    obj = json.loads(
        dump_work_ledger_line(_record(_FIXTURES[EnumWorkEventKind.HOLD_PLACED]()))
    )
    assert obj["event"]["scope"]["repos"] == ["omnibase_infra", "omnimarket"]
    assert obj["event"]["scope"]["lanes"] == ["merge-drain-7f", "runtime-train"]
    assert obj["event"]["blocks"] == ["arm", "merge"]
    assert obj["event"]["addressed_to"]["lanes"] == ["a-lane", "b-lane"]


def test_non_utc_offset_dumps_identically_to_its_utc_instant() -> None:
    utc = _record(_ruling())
    shifted = _record(
        _ruling().model_copy(
            update={"emitted_at": _EMITTED_AT.astimezone(timezone(timedelta(hours=-7)))}
        )
    )
    assert dump_work_ledger_line(shifted) == dump_work_ledger_line(utc)


def test_parse_accepts_one_trailing_newline() -> None:
    line = dump_work_ledger_line(_record(_ruling()))
    assert parse_work_ledger_line(line + "\n") == parse_work_ledger_line(line)


_TICKET_REQUIRED = frozenset(
    {
        EnumWorkEventKind.CLAIM_REQUESTED,
        EnumWorkEventKind.CLAIM_RELEASED,
        EnumWorkEventKind.FRICTION_RECORDED,
    }
)
_TZ_OFFSETS = st.integers(min_value=-14 * 60, max_value=14 * 60).map(
    lambda minutes: timezone(timedelta(minutes=minutes))
)
_AWARE = st.datetimes(
    min_value=datetime(2000, 1, 2),
    max_value=datetime(2099, 12, 30),
    timezones=_TZ_OFFSETS,
)
_TEXT = st.text(min_size=1, max_size=200).filter(lambda text: bool(text.strip()))


@settings(max_examples=300, deadline=None)
@given(
    kind=st.sampled_from(sorted(EnumWorkEventKind)),
    event_id=st.uuids(),
    emitted_at=_AWARE,
    summary=_TEXT,
    ticket_id=st.one_of(st.none(), st.from_regex(r"\AOMN-[1-9][0-9]{0,5}\Z")),
)
def test_round_trip_property(
    kind: EnumWorkEventKind,
    event_id: uuid.UUID,
    emitted_at: datetime,
    summary: str,
    ticket_id: str | None,
) -> None:
    fixture = _FIXTURES[kind]()
    update: dict[str, object] = {
        "event_id": event_id,
        "emitted_at": emitted_at,
        "summary": summary,
    }
    # Claim and friction events must name their ticket; the rest may omit it.
    if ticket_id is not None or kind not in _TICKET_REQUIRED:
        update["ticket_id"] = ticket_id
    # A lease must expire after it is placed; keep the fixture's lease one hour long.
    if kind is EnumWorkEventKind.HOLD_PLACED:
        update["expires_at"] = emitted_at + timedelta(hours=1)
    data = fixture.model_dump()
    data.update(update)
    event = type(fixture).model_validate(data)
    record = _record(event)
    line = dump_work_ledger_line(record)
    assert "\n" not in line
    parsed = parse_work_ledger_line(line)
    assert parsed == record
    assert dump_work_ledger_line(parsed) == line


# ---------------------------------------------------------------------------
# AC2 — every defect raises WorkLedgerParseError, never a partial record
# ---------------------------------------------------------------------------


def _good_obj() -> dict[str, object]:
    obj: dict[str, object] = json.loads(
        dump_work_ledger_line(_record(_FIXTURES[EnumWorkEventKind.HOLD_PLACED]()))
    )
    return obj


def _event(obj: dict[str, object]) -> dict[str, object]:
    event = obj["event"]
    assert isinstance(event, dict)
    return event


def _unknown_schema() -> str:
    obj = _good_obj()
    obj["schema"] = "onex.work-ledger/2"
    return json.dumps(obj)


def _missing_schema() -> str:
    obj = _good_obj()
    del obj["schema"]
    return json.dumps(obj)


def _unknown_kind() -> str:
    obj = _good_obj()
    _event(obj)["kind"] = "work.hold.extended"
    return json.dumps(obj)


def _extra_event_field() -> str:
    obj = _good_obj()
    _event(obj)["priority"] = "high"
    return json.dumps(obj)


def _extra_record_field() -> str:
    obj = _good_obj()
    obj["line_no"] = 7
    return json.dumps(obj)


def _schema_by_attribute_name() -> str:
    obj = _good_obj()
    obj["ledger_schema"] = obj.pop("schema")
    return json.dumps(obj)


def _naive_timestamp() -> str:
    obj = _good_obj()
    _event(obj)["emitted_at"] = "2026-09-24T13:30:05"
    return json.dumps(obj)


def _naive_nested_timestamp() -> str:
    obj = _good_obj()
    _event(obj)["expires_at"] = "2026-09-24T18:00:00"
    return json.dumps(obj)


def _trailing_garbage() -> str:
    return dump_work_ledger_line(_record(_ruling())) + " trailing"


def _two_records_on_one_line() -> str:
    line = dump_work_ledger_line(_record(_ruling()))
    return line + line


def _trailing_whitespace() -> str:
    return dump_work_ledger_line(_record(_ruling())) + " "


def _embedded_newline() -> str:
    return dump_work_ledger_line(_record(_ruling())) + "\n\n"


def _duplicate_key() -> str:
    line = dump_work_ledger_line(_record(_ruling()))
    return line[:-1] + ',"schema":"onex.work-ledger/1"}'


def _lax_coercion() -> str:
    obj: dict[str, object] = json.loads(
        dump_work_ledger_line(
            _record(_FIXTURES[EnumWorkEventKind.LEDGER_EPOCH_OPENED]())
        )
    )
    _event(obj)["epoch_seq"] = "0"
    return json.dumps(obj)


def _not_an_object() -> str:
    return "[1, 2, 3]"


def _empty() -> str:
    return ""


def _not_json() -> str:
    return "2026-09-24T13:30:05Z | HOLD | lane=x | repo=omnibase_infra"


def _nan_constant() -> str:
    obj: dict[str, object] = json.loads(
        dump_work_ledger_line(_record(_FIXTURES[EnumWorkEventKind.FRICTION_RECORDED]()))
    )
    return json.dumps(obj).replace('"0.10"', "NaN")


def _invalid_model() -> str:
    obj = _good_obj()
    _event(obj)["blocks"] = []
    return json.dumps(obj)


@pytest.mark.parametrize(
    "build",
    [
        _unknown_schema,
        _missing_schema,
        _unknown_kind,
        _extra_event_field,
        _extra_record_field,
        _schema_by_attribute_name,
        _naive_timestamp,
        _naive_nested_timestamp,
        _trailing_garbage,
        _two_records_on_one_line,
        _trailing_whitespace,
        _embedded_newline,
        _duplicate_key,
        _lax_coercion,
        _not_an_object,
        _empty,
        _not_json,
        _nan_constant,
        _invalid_model,
    ],
)
def test_defective_line_raises_parse_error(build: Callable[[], str]) -> None:
    with pytest.raises(WorkLedgerParseError):
        parse_work_ledger_line(build())


def test_parse_error_is_a_value_error() -> None:
    assert issubclass(WorkLedgerParseError, ValueError)


def test_good_object_parses() -> None:
    # Positive control for the defect cases: the object they all start from is valid.
    parsed = parse_work_ledger_line(json.dumps(_good_obj()))
    assert parsed.event.kind is EnumWorkEventKind.HOLD_PLACED


def test_record_requires_its_schema() -> None:
    with pytest.raises(ValidationError):
        ModelWorkLedgerRecord(event=_ruling())  # type: ignore[call-arg,arg-type]  # NOTE(OMN-16177): the missing schema is the case under test


# ---------------------------------------------------------------------------
# AC3 — the events path comes from one required variable, with no default
# ---------------------------------------------------------------------------


def test_events_path_variable_name() -> None:
    assert WORK_LEDGER_EVENTS_PATH_ENV == "ONEX_WORK_LEDGER_PATH"


def test_events_path_from_env_returns_the_variable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "ledger" / "ROLLING_WORK_LEDGER.jsonl"
    monkeypatch.setenv("ONEX_WORK_LEDGER_PATH", str(target))
    assert events_path_from_env() == target


def test_events_path_from_env_raises_key_error_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ONEX_WORK_LEDGER_PATH", raising=False)
    with pytest.raises(KeyError, match="ONEX_WORK_LEDGER_PATH"):
        events_path_from_env()


@pytest.mark.parametrize("blank", ["", "   "])
def test_events_path_from_env_refuses_blank(
    monkeypatch: pytest.MonkeyPatch, blank: str
) -> None:
    # A blank value would become Path("."), a silent default by another name.
    monkeypatch.setenv("ONEX_WORK_LEDGER_PATH", blank)
    with pytest.raises(KeyError, match="ONEX_WORK_LEDGER_PATH"):
        events_path_from_env()
