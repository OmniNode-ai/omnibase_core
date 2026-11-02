# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The stale-hold rule and the claim answers it leaves alone (OMN-21947, plan L3).

An open-ended hold (no ``expires_at``) that nothing released and that is older than 14
days is stale: the queries list it apart with its age and do not treat it as in force.
Settled operator rule: an open-ended hold older than 14 days counts as stale.
One test per class of hold, and the claim classes the rule must not touch.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.enums.enum_work_ledger_verdict_status import (
    EnumWorkLedgerVerdictStatus as S,
)
from omnibase_core.models.events.work import (
    ModelHoldScope,
    ModelPrKey,
    ModelRecipients,
    ModelWorkEvent,
    ModelWorkHoldPlaced,
)
from omnibase_core.models.nodes.work_ledger_state import (
    ModelWorkLedgerFoldInput,
    ModelWorkLedgerState,
)
from omnibase_core.nodes.node_work_ledger_state_compute import (
    NodeWorkLedgerStateCompute,
)
from omnibase_core.nodes.node_work_ledger_state_compute.queries import (
    STALE_HOLD_AGE,
    holds,
    inbox,
    is_held,
    open_claims,
    pauses_in_force,
)

from .work_ledger_events import (
    T0,
    claim,
    eid,
    epoch,
    hold,
    line,
    release,
)

MERGE = EnumHoldBlock.MERGE
INFRA_1 = ModelPrKey(repo="omnibase_infra", number=1)
NOW = T0 + timedelta(days=30)


def _fold(*events: ModelWorkEvent, as_of: datetime = NOW) -> ModelWorkLedgerState:
    lines = tuple(line(event) for event in events)
    return NodeWorkLedgerStateCompute().handle(
        ModelWorkLedgerFoldInput(lines=lines, as_of=as_of)
    )


def _repo_hold(
    n: int, *, age: timedelta, addressed_to: ModelRecipients | None = None
) -> ModelWorkHoldPlaced:
    return hold(
        eid(n),
        ModelHoldScope(repos=frozenset({"omnibase_infra"})),
        emitted_at=NOW - age,
        addressed_to=addressed_to,
    )


def test_stale_age_is_fourteen_days() -> None:
    assert timedelta(days=14) == STALE_HOLD_AGE


def test_hold_class_stale_open_hold_is_listed_apart_with_its_age() -> None:
    state = _fold(epoch(), _repo_hold(1, age=timedelta(days=20)))

    verdict = holds(state, as_of=NOW)

    assert verdict.status is S.CLEAR
    assert verdict.holds == ()
    assert [(stale.hold.hold.event_id, stale.age) for stale in verdict.stale_holds] == [
        (eid(1), timedelta(days=20))
    ]


def test_hold_class_stale_open_hold_is_not_in_force_for_the_pause_check() -> None:
    state = _fold(epoch(), _repo_hold(1, age=timedelta(days=20)))

    assert is_held(state, INFRA_1, MERGE, True, as_of=NOW).status is S.CLEAR
    assert pauses_in_force(state, "omnibase_infra", True, as_of=NOW).status is S.CLEAR
    stale = is_held(state, INFRA_1, MERGE, True, as_of=NOW).stale_holds
    assert [entry.hold.hold.event_id for entry in stale] == [eid(1)]


def test_hold_class_fresh_open_hold_stays_in_force() -> None:
    state = _fold(epoch(), _repo_hold(1, age=timedelta(days=3)))

    verdict = holds(state, as_of=NOW)

    assert verdict.status is S.HELD
    assert [h.hold.event_id for h in verdict.holds] == [eid(1)]
    assert verdict.stale_holds == ()


def test_hold_class_exactly_fourteen_days_is_still_in_force() -> None:
    state = _fold(epoch(), _repo_hold(1, age=STALE_HOLD_AGE))

    assert holds(state, as_of=NOW).status is S.HELD
    assert holds(state, as_of=NOW).stale_holds == ()


def test_hold_class_released_old_hold_is_neither_in_force_nor_stale() -> None:
    state = _fold(
        epoch(),
        _repo_hold(1, age=timedelta(days=20)),
        release(eid(2), eid(1), emitted_at=NOW - timedelta(days=19)),
    )

    verdict = holds(state, as_of=NOW)

    assert verdict.status is S.CLEAR
    assert verdict.holds == ()
    assert verdict.stale_holds == ()


def test_hold_class_partially_released_old_hold_has_a_release_and_is_not_stale() -> (
    None
):
    state = _fold(
        epoch(),
        _repo_hold(1, age=timedelta(days=20)),
        release(
            eid(2),
            eid(1),
            partial=ModelHoldScope(prs=frozenset({INFRA_1})),
            emitted_at=NOW - timedelta(days=19),
        ),
    )

    verdict = holds(state, as_of=NOW)

    assert verdict.status is S.HELD
    assert verdict.stale_holds == ()


def test_hold_class_lease_with_an_expiry_is_never_stale() -> None:
    state = _fold(
        epoch(),
        hold(
            eid(1),
            ModelHoldScope(surfaces=frozenset({"dogfood-105"})),
            emitted_at=NOW - timedelta(days=40),
            expires_at=NOW - timedelta(days=39),
        ),
    )

    verdict = holds(state, as_of=NOW)

    assert verdict.status is S.HELD
    assert verdict.stale_holds == ()


def test_hold_class_without_a_clock_nothing_is_judged_stale() -> None:
    state = _fold(epoch(), _repo_hold(1, age=timedelta(days=90)))

    assert is_held(state, INFRA_1, MERGE, True).status is S.HELD
    assert is_held(state, INFRA_1, MERGE, True).stale_holds == ()


def test_hold_class_stale_addressed_hold_leaves_the_inbox() -> None:
    from omnibase_core.models.events.work import ModelRecipients

    state = _fold(
        epoch(),
        _repo_hold(
            1,
            age=timedelta(days=20),
            addressed_to=ModelRecipients(lanes=frozenset({"lane-b"})),
        ),
    )

    assert inbox(state, "lane-b", as_of=NOW).status is S.CLEAR
    assert inbox(state, "lane-b").status is S.FOUND


def test_claim_class_an_old_open_claim_is_not_made_stale_by_the_hold_rule() -> None:
    state = _fold(epoch(), claim(eid(1), "OMN-1"))

    verdict = open_claims(state, ticket_id="OMN-1")

    assert verdict.status is S.FOUND
    assert [c.event_id for c in verdict.claims] == [eid(1)]
    assert verdict.stale_holds == ()
