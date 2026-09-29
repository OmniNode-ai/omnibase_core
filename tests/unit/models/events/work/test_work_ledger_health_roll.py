# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``health`` and the roll invariant (OMN-16177, plan task M4).

The roll moves closed events out of the live file into an archive. The plan's
invariant is ``fold(archive union live) == fold(live)`` for every query. The
second review noted that ``health`` reports the count of invalid releases and a
roll drops closed invalid releases. The check here goes further: ``health`` also
counts lines and events, which differ after any roll that archives anything, so
carrying invalid releases through the roll could not make ``health`` invariant.
The choice is therefore to exclude ``health`` from the invariant by name, and to
spell that name once, in ``ROLL_INVARIANT_EXCLUDED_QUERIES``, for the roll's
property test to import.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.models.events.work import (
    ModelHoldScope,
    ModelPrKey,
    ModelRecipients,
)
from omnibase_core.models.nodes.work_ledger_state import (
    ModelWorkLedgerFoldInput,
    ModelWorkLedgerState,
)
from omnibase_core.nodes.node_work_ledger_state_compute import (
    NodeWorkLedgerStateCompute,
    queries,
)
from tests.unit.nodes.node_work_ledger_state_compute.work_ledger_events import (
    claim,
    claim_release,
    eid,
    epoch,
    hold,
    line,
    message,
    question,
    release,
)

pytestmark = pytest.mark.unit

_PR = ModelPrKey(repo="omnibase_infra", number=1)
_KEPT = (
    line(epoch()),
    line(hold(eid(1), ModelHoldScope(repos=frozenset({"omnibase_infra"})))),
    line(claim(eid(2), "OMN-1")),
    line(message(eid(3), ModelRecipients(lanes=frozenset({"lane-a"})))),
    line(question(eid(4))),
)
# What a roll archives: a closed claim pair, and a release that names no hold.
_ROLLED = (
    line(claim(eid(5), "OMN-2")),
    line(claim_release(eid(6), "OMN-2", eid(5))),
    line(release(eid(7), eid(999))),
)

_QUERY_CALLS: dict[str, Callable[[ModelWorkLedgerState], object]] = {
    "is_held": lambda s: queries.is_held(s, _PR, EnumHoldBlock.MERGE, True),
    "pauses_in_force": lambda s: queries.pauses_in_force(s, "omnibase_infra", True),
    "open_claims": lambda s: queries.open_claims(s, ticket_id="OMN-1"),
    "inbox": lambda s: queries.inbox(s, "lane-a"),
    "surface_lease": lambda s: queries.surface_lease(s, "dogfood-105"),
    "questions": lambda s: queries.questions(s),
    "health": lambda s: queries.health(s),
}


def _fold(*lines: str) -> ModelWorkLedgerState:
    return NodeWorkLedgerStateCompute().handle(ModelWorkLedgerFoldInput(lines=lines))


def test_health_query_table_covers_every_state_query() -> None:
    """A new query has to be added to this table, and so to the roll decision."""
    assert set(_QUERY_CALLS) == set(queries.__all__) - {
        "actor_lane",
        "ROLL_INVARIANT_EXCLUDED_QUERIES",
    }


def test_health_is_the_one_query_a_roll_changes() -> None:
    excluded = queries.ROLL_INVARIANT_EXCLUDED_QUERIES

    before_roll = _fold(*_KEPT, *_ROLLED)
    after_roll = _fold(*_KEPT)
    assert before_roll.decidable and after_roll.decidable
    assert len(before_roll.invalid_releases) == 1  # control: the release is invalid
    assert not after_roll.invalid_releases

    changed = {
        name
        for name, call in _QUERY_CALLS.items()
        if call(before_roll) != call(after_roll)
    }

    assert changed == {"health"}
    assert excluded == frozenset({"health"})
    assert changed == excluded


def test_health_differs_on_counts_too_so_carrying_releases_cannot_fix_it() -> None:
    before_roll = queries.health(_fold(*_KEPT, *_ROLLED))
    after_roll = queries.health(_fold(*_KEPT))

    differing = {
        field
        for field in type(before_roll).model_fields
        if getattr(before_roll, field) != getattr(after_roll, field)
    }

    assert differing == {"line_count", "event_count", "invalid_release_count"}
