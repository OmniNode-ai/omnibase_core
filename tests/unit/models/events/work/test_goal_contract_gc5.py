# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Goal contract event spine tests (OMN-20028, GC.5)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import cast

import pytest
from pydantic import TypeAdapter, ValidationError

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.enums.enum_work_outcome import EnumWorkOutcome
from omnibase_core.models.events.work import (
    WORK_EVENT_PARTITION_KEY_FIELDS,
    ModelSessionActor,
    ModelWorkClaimRequested,
    ModelWorkEvent,
    ModelWorkGoalRevised,
    ModelWorkResultRecorded,
)
from omnibase_core.models.events.work.model_work_ledger_render import (
    ROW_TYPE_BY_KIND,
    index_events,
    render_ledger_row,
)
from omnibase_core.models.nodes.work_ledger_state.model_work_ledger_state import (
    ModelWorkLedgerState,
)
from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem
from omnibase_core.nodes.node_work_ledger_state_compute.handler import (
    fold_work_events,
)

pytestmark = pytest.mark.unit

_AT = datetime(2026, 9, 29, 20, 0, tzinfo=UTC)
_ACTOR = ModelSessionActor(session_handle="gc5-test", agent_kind="test")
_ITEM = ModelContractDodItem(
    id="behavior",
    description="The behavior is proven by the focused test.",
    binds_ac=("AC1",),
)


def _claim(
    *, event_id: uuid.UUID | None = None, ticket_id: str = "OMN-20028"
) -> ModelWorkClaimRequested:
    return ModelWorkClaimRequested(
        event_id=event_id or uuid.uuid4(),
        emitted_at=_AT,
        actor=_ACTOR,
        ticket_id=ticket_id,
        summary="open the goal",
        dod_evidence=(_ITEM,),
        contract_schema_version="1.0.0",
    )


def _revision(
    goal_id: uuid.UUID,
    replaces: uuid.UUID,
    *,
    event_id: uuid.UUID | None = None,
    ticket_id: str = "OMN-20028",
    reason: str = "Update the acceptance contract.",
) -> ModelWorkGoalRevised:
    return ModelWorkGoalRevised(
        event_id=event_id or uuid.uuid4(),
        emitted_at=_AT,
        actor=_ACTOR,
        ticket_id=ticket_id,
        summary="revise the goal",
        goal_id=goal_id,
        dod_evidence=(_ITEM,),
        contract_schema_version="1.0.0",
        reason=reason,
        replaces=replaces,
    )


def _result(
    closes_claims: frozenset[uuid.UUID],
    contract_revision: uuid.UUID | None = None,
) -> ModelWorkResultRecorded:
    return ModelWorkResultRecorded(
        event_id=uuid.uuid4(),
        emitted_at=_AT,
        actor=_ACTOR,
        ticket_id="OMN-20028",
        summary="close named goal revision",
        outcome=EnumWorkOutcome.LANDED,
        closes_claims=closes_claims,
        contract_revision=contract_revision,
        friction_none=True,
    )


def test_legacy_claim_fixtures_parse_and_goal_contract_union_round_trip() -> None:
    claim = _claim()
    adapter = TypeAdapter(ModelWorkEvent)
    restored = adapter.validate_json(claim.model_dump_json())
    assert restored == claim
    assert isinstance(restored, ModelWorkClaimRequested)
    assert restored.dod_evidence == (_ITEM,)
    assert restored.parent_goal_id is None

    # Captured v1 claim payload: the event shape that was persisted before the
    # additive goal-contract fields existed.
    legacy_payload = {
        "kind": "work.claim.requested",
        "event_id": "11111111-1111-4111-8111-111111111111",
        "emitted_at": "2026-09-24T13:30:05.123456Z",
        "actor": {
            "kind": "session",
            "session_handle": "typed-ledger-t3",
            "controller_id": "e2583369-b006-4c23-9a79-b13061f0ea09",
            "agent_kind": "build-lane",
        },
        "actor_key": "session:typed-ledger-t3",
        "ticket_id": "OMN-16177",
        "summary": "typed ledger task T3",
        "proof_class": None,
        "prs": [],
        "scope_text": None,
        "est_lane_hours": None,
        "displaces": None,
        "consent_ref": None,
    }
    legacy = adapter.validate_python(legacy_payload)
    assert isinstance(legacy, ModelWorkClaimRequested)
    assert legacy.dod_evidence == ()
    assert legacy.parent_goal_id is None
    assert legacy.contract_schema_version is None


def test_goal_claim_requires_validated_schema_version() -> None:
    payload = _claim().model_dump(mode="python")
    payload.pop("contract_schema_version")
    with pytest.raises(ValidationError, match="contract_schema_version"):
        ModelWorkClaimRequested.model_validate(payload)

    payload["contract_schema_version"] = "1.0.0-preview"
    with pytest.raises(ValidationError, match="schema_version"):
        ModelWorkClaimRequested.model_validate(payload)

    payload["contract_schema_version"] = {"major": 1, "minor": 0, "patch": 0}
    with pytest.raises(ValidationError, match="must be a SemVer string"):
        ModelWorkClaimRequested.model_validate(payload)


def test_goal_schema_version_wire_format_is_canonical_string() -> None:
    claim = _claim()
    revision = _revision(claim.event_id, claim.event_id)
    for event in (claim, revision):
        payload = json.loads(event.model_dump_json())
        assert payload["contract_schema_version"] == "1.0.0"
        assert (
            TypeAdapter(ModelWorkEvent).validate_json(event.model_dump_json()) == event
        )

    revision_payload = ModelWorkGoalRevised.model_json_schema(mode="serialization")
    version_schema = revision_payload["properties"]["contract_schema_version"]
    assert version_schema["type"] == "string"


def test_goal_revision_requires_nonblank_reason_and_round_trips_union() -> None:
    claim = _claim()
    revision = _revision(claim.event_id, claim.event_id)
    restored = TypeAdapter(ModelWorkEvent).validate_json(revision.model_dump_json())
    assert restored == revision
    payload = revision.model_dump(mode="python")
    payload.pop("reason")
    with pytest.raises(ValidationError, match="reason"):
        ModelWorkGoalRevised.model_validate(payload)
    with pytest.raises(ValidationError, match="reason"):
        _revision(claim.event_id, claim.event_id, reason="   ")
    invalid_version = revision.model_dump(mode="python")
    invalid_version["contract_schema_version"] = "1.0.0-preview"
    with pytest.raises(ValidationError, match="schema_version"):
        ModelWorkGoalRevised.model_validate(invalid_version)


def test_goal_revision_chain_keeps_history_and_flags_fork() -> None:
    claim = _claim()
    first = _revision(claim.event_id, claim.event_id)
    second = _revision(claim.event_id, first.event_id)
    fork = _revision(claim.event_id, claim.event_id)

    events: list[ModelWorkEvent] = [claim, first, second, fork, first]
    state = fold_work_events(events, line_count=len(events))
    reordered = fold_work_events(list(reversed(events)), line_count=len(events))

    assert isinstance(state, ModelWorkLedgerState)
    assert state.goal_revisions == reordered.goal_revisions
    assert state.undecided_reasons == reordered.undecided_reasons
    assert {event.event_id for event in state.goal_revisions} == {
        first.event_id,
        second.event_id,
        fork.event_id,
    }
    assert any(
        "goal revision fork" in reason
        and str(first.replaces) in reason
        and str(first.event_id) in reason
        and str(fork.event_id) in reason
        for reason in state.undecided_reasons
    )
    assert second.replaces == first.event_id


def test_goal_revision_self_cycle_makes_ledger_undecided() -> None:
    claim = _claim()
    revision = _revision(
        claim.event_id,
        claim.event_id,
        event_id=uuid.uuid4(),
    )
    self_cycle = revision.model_copy(update={"replaces": revision.event_id})

    state = fold_work_events([claim, self_cycle])

    assert self_cycle in state.goal_revisions
    assert any(
        "goal revision cycle" in reason and str(self_cycle.event_id) in reason
        for reason in state.undecided_reasons
    )


def test_goal_revision_multi_edge_cycle_makes_ledger_undecided() -> None:
    claim = _claim()
    revision_a_id = uuid.uuid4()
    revision_b_id = uuid.uuid4()
    revision_c_id = uuid.uuid4()
    revision_a = _revision(
        claim.event_id,
        revision_b_id,
        event_id=revision_a_id,
    )
    revision_b = _revision(
        claim.event_id,
        revision_c_id,
        event_id=revision_b_id,
    )
    revision_c = _revision(
        claim.event_id,
        revision_a_id,
        event_id=revision_c_id,
    )

    state = fold_work_events([claim, revision_a, revision_b, revision_c])

    assert {event.event_id for event in state.goal_revisions} == {
        revision_a_id,
        revision_b_id,
        revision_c_id,
    }
    assert any(
        "goal revision cycle" in reason
        and all(
            str(event_id) in reason
            for event_id in (revision_a_id, revision_b_id, revision_c_id)
        )
        for reason in state.undecided_reasons
    )


def test_result_closes_explicit_contract_revision() -> None:
    claim = _claim()
    revision = _revision(claim.event_id, claim.event_id)
    result = ModelWorkResultRecorded(
        event_id=uuid.uuid4(),
        emitted_at=_AT,
        actor=_ACTOR,
        ticket_id="OMN-20028",
        summary="close the named revision",
        outcome=EnumWorkOutcome.LANDED,
        closes_claims=frozenset({claim.event_id}),
        contract_revision=revision.event_id,
        friction_none=True,
    )
    restored = TypeAdapter(ModelWorkEvent).validate_json(result.model_dump_json())
    assert isinstance(restored, ModelWorkResultRecorded)
    assert restored.contract_revision == revision.event_id
    assert restored.closes_claims == frozenset({claim.event_id})


def test_contract_bearing_result_requires_explicit_revision_binding() -> None:
    claim = _claim()
    result = _result(frozenset({claim.event_id}))
    events: list[ModelWorkEvent] = [claim, result, result]

    state = fold_work_events(events)
    reordered = fold_work_events(list(reversed(events)))

    assert state.open_claims == reordered.open_claims == (claim,)
    assert state.undecided_reasons == reordered.undecided_reasons
    assert any(
        "without contract_revision" in reason for reason in state.undecided_reasons
    )
    assert state.event_count == 2


def test_contract_bearing_result_rejects_unknown_revision() -> None:
    claim = _claim()
    result = _result(frozenset({claim.event_id}), uuid.uuid4())

    state = fold_work_events([claim, result])

    assert state.open_claims == (claim,)
    assert any(
        "unknown contract_revision" in reason for reason in state.undecided_reasons
    )


def test_contract_bearing_result_checks_each_claim_against_its_revision() -> None:
    claim = _claim()
    other_claim = _claim()
    revision = _revision(claim.event_id, claim.event_id)
    result = _result(
        frozenset({claim.event_id, other_claim.event_id}), revision.event_id
    )

    state = fold_work_events([claim, other_claim, revision, result])

    assert claim not in state.open_claims
    assert other_claim in state.open_claims
    assert any(
        "does not follow a valid revision chain" in reason
        for reason in state.undecided_reasons
    )


def test_revision_with_missing_parent_cannot_authorize_contract_closure() -> None:
    claim = _claim()
    orphan = _revision(claim.event_id, uuid.uuid4())
    result = _result(frozenset({claim.event_id}), orphan.event_id)

    state = fold_work_events([result, orphan, claim])

    assert claim in state.open_claims
    assert any(
        "replaces missing revision" in reason for reason in state.undecided_reasons
    )
    assert any(
        "does not follow a valid revision chain" in reason
        for reason in state.undecided_reasons
    )


def test_cyclic_revision_cannot_authorize_contract_closure() -> None:
    claim = _claim()
    first_id = uuid.uuid4()
    second_id = uuid.uuid4()
    first = _revision(claim.event_id, second_id, event_id=first_id)
    second = _revision(claim.event_id, first_id, event_id=second_id)
    result = _result(frozenset({claim.event_id}), first.event_id)
    events: list[ModelWorkEvent] = [claim, first, second, result, first]

    state = fold_work_events(events)
    reordered = fold_work_events(list(reversed(events)))

    assert state.open_claims == reordered.open_claims == (claim,)
    assert state.undecided_reasons == reordered.undecided_reasons
    assert any("goal revision cycle" in reason for reason in state.undecided_reasons)
    assert any(
        "does not follow a valid revision chain" in reason
        for reason in state.undecided_reasons
    )


def test_opening_claim_id_is_a_valid_explicit_close_binding() -> None:
    claim = _claim()
    result = _result(frozenset({claim.event_id}), claim.event_id)

    state = fold_work_events([result, claim])

    assert state.open_claims == ()
    assert not any("contract_revision" in reason for reason in state.undecided_reasons)


def test_historical_same_goal_revision_is_a_valid_explicit_close_binding() -> None:
    claim = _claim()
    first = _revision(claim.event_id, claim.event_id)
    second = _revision(claim.event_id, first.event_id)
    result = _result(frozenset({claim.event_id}), first.event_id)

    events: list[ModelWorkEvent] = [result, second, claim, first, second]
    state = fold_work_events(events)
    reordered = fold_work_events(list(reversed(events)))

    assert state.open_claims == reordered.open_claims == ()
    assert state.goal_revisions == reordered.goal_revisions
    assert {event.event_id for event in state.goal_revisions} == {
        first.event_id,
        second.event_id,
    }
    assert not any("contract_revision" in reason for reason in state.undecided_reasons)


def test_legacy_empty_contract_result_without_revision_still_closes_claim() -> None:
    claim = ModelWorkClaimRequested(
        event_id=uuid.uuid4(),
        emitted_at=_AT,
        actor=_ACTOR,
        ticket_id="OMN-16177",
        summary="legacy claim",
    )
    result = _result(frozenset({claim.event_id}))

    state = fold_work_events([claim, result])

    assert state.open_claims == ()
    assert not any("contract_revision" in reason for reason in state.undecided_reasons)


def test_every_kind_partitioned_and_rendered() -> None:
    claim = _claim()
    revision = _revision(claim.event_id, claim.event_id)
    assert (
        WORK_EVENT_PARTITION_KEY_FIELDS[revision.kind]
        == (WORK_EVENT_PARTITION_KEY_FIELDS[claim.kind])
    )
    assert revision.kind in ROW_TYPE_BY_KIND
    rendered = render_ledger_row(revision, index_events([claim, revision]))
    assert "goal=" + str(claim.event_id) in rendered
    assert "contract-schema=1.0.0" in rendered
    assert "replaces=" + str(claim.event_id) in rendered
    assert "reason=Update the acceptance contract." in rendered


def test_goal_revised_kind_is_registered_once() -> None:
    assert sum(kind is EnumWorkEventKind.GOAL_REVISED for kind in ROW_TYPE_BY_KIND) == 1
    assert cast(str, ROW_TYPE_BY_KIND[EnumWorkEventKind.GOAL_REVISED]) == "STATUS"
