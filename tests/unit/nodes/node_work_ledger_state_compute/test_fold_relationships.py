# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Ruling relationships and correction closure in the fold (OMN-21107, TA.5).

- A supersedes link closes its ruling-or-consent target; amends and extends
  never close. Every valid link lands in ``links``; a reference naming an
  unknown event, or a non-ruling where a ruling is required, is refused,
  creates no link and closes nothing.
- A correction never closes: it names its target in ``corrected_events`` of any
  kind, carries its ``operator_span`` on the CORRECTS link, and a ruling or
  consent target also lists it in its own state.
- The fold is set-based: every permutation of a ledger mixing all four
  relations folds to the same state.
"""

from __future__ import annotations

import json
import uuid
from itertools import permutations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_invalid_relationship_reason import (
    EnumInvalidRelationshipReason,
)
from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.enums.enum_work_ledger_relation import EnumWorkLedgerRelation
from omnibase_core.models.events.work import (
    ModelHoldScope,
    ModelWorkEvent,
    parse_work_ledger_line,
)
from omnibase_core.models.nodes.work_ledger_state import (
    ModelCorrectedEvent,
    ModelRulingState,
    ModelWorkLedgerState,
)
from omnibase_core.nodes.node_work_ledger_state_compute.handler import (
    fold_work_events,
)

from .work_ledger_events import (
    consent,
    correction,
    eid,
    epoch,
    hold,
    line,
    ruling,
)

pytestmark = pytest.mark.unit

_SUPERSEDES = EnumWorkLedgerRelation.SUPERSEDES
_AMENDS = EnumWorkLedgerRelation.AMENDS
_EXTENDS = EnumWorkLedgerRelation.EXTENDS
_CORRECTS = EnumWorkLedgerRelation.CORRECTS

_HOLD_SCOPE = ModelHoldScope(repos=frozenset({"omnibase_core"}))


def _fold(*events: ModelWorkEvent) -> ModelWorkLedgerState:
    return fold_work_events([epoch(), *events])


def _ruling(state: ModelWorkLedgerState, event_id: uuid.UUID) -> ModelRulingState:
    (match,) = [r for r in state.rulings if r.ruling.event_id == event_id]
    return match


def _corrected(state: ModelWorkLedgerState, target: uuid.UUID) -> ModelCorrectedEvent:
    (match,) = [c for c in state.corrected_events if c.target == target]
    return match


# ---------------------------------------------------------------------------
# Ruling relationships
# ---------------------------------------------------------------------------


def test_superseded_ruling_is_closed_and_names_the_superseder() -> None:
    state = _fold(ruling(eid(1)), ruling(eid(2), supersedes=eid(1)))
    superseded = _ruling(state, eid(1))
    assert not superseded.is_open
    assert superseded.superseded_by == (eid(2),)
    assert _ruling(state, eid(2)).is_open
    (link,) = state.links
    assert (link.source, link.target, link.relation) == (eid(2), eid(1), _SUPERSEDES)


def test_amended_ruling_stays_open() -> None:
    state = _fold(ruling(eid(1)), ruling(eid(2), amends=eid(1)))
    amended = _ruling(state, eid(1))
    assert amended.is_open
    assert amended.amended_by == (eid(2),)
    (link,) = state.links
    assert (link.source, link.target, link.relation) == (eid(2), eid(1), _AMENDS)


def test_consent_extended_by_a_later_consent_stays_open() -> None:
    state = _fold(consent(eid(1)), consent(eid(2), extends=eid(1)))
    extended = _ruling(state, eid(1))
    assert extended.is_open
    assert extended.extended_by == (eid(2),)
    (link,) = state.links
    assert (link.source, link.target, link.relation) == (eid(2), eid(1), _EXTENDS)


def test_consent_superseded_by_a_ruling_is_closed() -> None:
    state = _fold(consent(eid(1)), ruling(eid(2), supersedes=eid(1)))
    assert not _ruling(state, eid(1)).is_open
    assert _ruling(state, eid(1)).superseded_by == (eid(2),)


# ---------------------------------------------------------------------------
# Correction closure
# ---------------------------------------------------------------------------


def test_corrected_ruling_stays_open_and_lists_the_correction() -> None:
    state = _fold(
        ruling(eid(1)),
        correction(eid(2), corrects=eid(1), operator_span="not what I said"),
    )
    corrected = _ruling(state, eid(1))
    assert corrected.is_open
    assert corrected.corrected_by == (eid(2),)
    entry = _corrected(state, eid(1))
    assert entry.target_kind is EnumWorkEventKind.RULING_RECORDED
    assert [c.event_id for c in entry.corrected_by] == [eid(2)]
    (link,) = state.links
    assert (link.source, link.target, link.relation) == (eid(2), eid(1), _CORRECTS)
    assert link.operator_span == "not what I said"


def test_correction_of_a_hold_keeps_the_hold_in_force() -> None:
    placed = hold(eid(1), _HOLD_SCOPE)
    state = _fold(placed, correction(eid(2), corrects=eid(1)))
    assert [h.hold.event_id for h in state.holds_in_force] == [eid(1)]
    entry = _corrected(state, eid(1))
    assert entry.target_kind is EnumWorkEventKind.HOLD_PLACED
    assert [c.event_id for c in entry.corrected_by] == [eid(2)]


# ---------------------------------------------------------------------------
# Refused references
# ---------------------------------------------------------------------------


def test_supersedes_naming_an_unknown_id_is_refused_and_closes_nothing() -> None:
    state = _fold(ruling(eid(1)), ruling(eid(2), supersedes=eid(99)))
    assert state.links == ()
    assert _ruling(state, eid(1)).is_open
    assert _ruling(state, eid(2)).is_open
    (invalid,) = state.invalid_relationship_refs
    assert (invalid.referrer, invalid.target, invalid.relation) == (
        eid(2),
        eid(99),
        _SUPERSEDES,
    )
    assert invalid.reason is EnumInvalidRelationshipReason.UNKNOWN_TARGET


def test_supersedes_naming_a_hold_is_not_a_ruling() -> None:
    placed = hold(eid(1), _HOLD_SCOPE)
    state = _fold(placed, ruling(eid(2), supersedes=eid(1)))
    (invalid,) = state.invalid_relationship_refs
    assert invalid.reason is EnumInvalidRelationshipReason.NOT_A_RULING
    assert invalid.relation is _SUPERSEDES
    assert state.links == ()


def test_corrects_naming_an_unknown_id_is_refused() -> None:
    state = _fold(correction(eid(1), corrects=eid(99)))
    (invalid,) = state.invalid_relationship_refs
    assert invalid.reason is EnumInvalidRelationshipReason.UNKNOWN_TARGET
    assert invalid.relation is _CORRECTS
    assert state.links == ()
    assert state.corrected_events == ()


def test_legacy_only_correction_creates_nothing() -> None:
    state = _fold(ruling(eid(1)), correction(eid(2), corrects_legacy_ts="14:02"))
    assert state.links == ()
    assert state.corrected_events == ()
    assert state.invalid_relationship_refs == ()
    assert _ruling(state, eid(1)).is_open


# ---------------------------------------------------------------------------
# AC4 — the fold is set-based
# ---------------------------------------------------------------------------

_MIXED: tuple[ModelWorkEvent, ...] = (
    ruling(eid(1)),
    ruling(eid(2), supersedes=eid(1)),
    ruling(eid(3), amends=eid(1)),
    consent(eid(4), extends=eid(1)),
    correction(eid(5), corrects=eid(1), operator_span="the quoted words"),
)


def test_every_permutation_folds_to_the_same_state() -> None:
    baseline = _fold(*_MIXED).model_dump()
    baseline.pop("line_count")
    for order in permutations(_MIXED):
        state = _fold(*order).model_dump()
        state.pop("line_count")
        assert state == baseline


# ---------------------------------------------------------------------------
# Serialization round trip and self-reference
# ---------------------------------------------------------------------------


def test_line_round_trip_preserves_the_relationship_fields() -> None:
    rich = consent(eid(1), supersedes=eid(2), amends=eid(3), extends=eid(4))
    assert parse_work_ledger_line(line(rich)).event == rich
    spanned = correction(eid(5), corrects=eid(1), operator_span="the exact words")
    assert parse_work_ledger_line(line(spanned)).event == spanned


def test_events_without_relationships_serialize_without_the_new_keys() -> None:
    plain_ruling = json.loads(line(ruling(eid(1))))["event"]
    assert "extends" not in plain_ruling
    plain_consent = json.loads(line(consent(eid(2))))["event"]
    assert not {"supersedes", "amends", "extends"} & plain_consent.keys()


def test_a_consent_cannot_supersede_itself() -> None:
    with pytest.raises(ValidationError):
        consent(eid(1), supersedes=eid(1))


def test_a_ruling_cannot_extend_itself() -> None:
    with pytest.raises(ValidationError):
        ruling(eid(1), extends=eid(1))
