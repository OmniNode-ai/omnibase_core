# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The work-ledger fold and its queries, case by case (OMN-19405, plan T4).

Covers AC5 (every doubt answers UNDECIDED, never CLEAR), AC6 (the handler
imports no envelope), and the fold semantics of the plan's section 5.3: full
and partial releases, refused releases, claims, inboxes, surface leases,
pauses with exemptions, and the health summary.
"""

from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.enums.enum_invalid_release_reason import EnumInvalidReleaseReason
from omnibase_core.enums.enum_surface_result import EnumSurfaceResult
from omnibase_core.enums.enum_work_ledger_verdict_status import (
    EnumWorkLedgerVerdictStatus,
)
from omnibase_core.models.events.work import (
    ModelHoldScope,
    ModelPrKey,
    ModelRecipients,
    ModelWorkEvent,
)
from omnibase_core.models.nodes.work_ledger_state import (
    ModelWorkLedgerFoldInput,
    ModelWorkLedgerState,
)
from omnibase_core.nodes.node_work_ledger_state_compute import (
    NodeWorkLedgerStateCompute,
    handler,
)
from omnibase_core.nodes.node_work_ledger_state_compute.handler import (
    NO_EPOCH_REASON,
    complete_ledger_lines,
    fold_work_events,
)
from omnibase_core.nodes.node_work_ledger_state_compute.queries import (
    health,
    inbox,
    is_held,
    open_claims,
    pauses_in_force,
    surface_lease,
)

from .work_ledger_events import (
    T0,
    ack,
    claim,
    claim_release,
    eid,
    epoch,
    hold,
    line,
    message,
    pr,
    release,
    result,
)

pytestmark = pytest.mark.unit

S = EnumWorkLedgerVerdictStatus
MERGE = EnumHoldBlock.MERGE
INFRA_1 = pr("omnibase_infra", 1)
INFRA_2 = pr("omnibase_infra", 2)
MARKET_1 = pr("omnimarket", 1)


def _fold(*lines: str, as_of: datetime | None = None) -> ModelWorkLedgerState:
    return NodeWorkLedgerStateCompute().handle(
        ModelWorkLedgerFoldInput(lines=lines, as_of=as_of)
    )


def _held(state: ModelWorkLedgerState, key: ModelPrKey = INFRA_1) -> S:
    return is_held(state, key, MERGE, runtime_affecting=True).status


REPO_HOLD = hold(eid(1), ModelHoldScope(repos=frozenset({"omnibase_infra"})))


# --------------------------------------------------------------------------- #
# AC5: every doubt answers UNDECIDED, never CLEAR
# --------------------------------------------------------------------------- #


def _all_verdicts(state: ModelWorkLedgerState) -> list[S]:
    return [
        is_held(state, INFRA_1, MERGE, runtime_affecting=False).status,
        pauses_in_force(state, "omnibase_infra", runtime_affecting=False).status,
        open_claims(state, ticket_id="OMN-1").status,
        inbox(state, "lane-a").status,
        surface_lease(state, "dogfood-105").status,
    ]


_UNKNOWN_KIND = json.dumps(
    {
        "schema": "onex.work-ledger/1",
        "event": {**json.loads(line(REPO_HOLD))["event"], "kind": "work.hold.future"},
    },
    sort_keys=True,
    separators=(",", ":"),
)
_UNKNOWN_SCHEMA = line(REPO_HOLD).replace("onex.work-ledger/1", "onex.work-ledger/2")
_CONFLICT = line(
    hold(eid(1), ModelHoldScope(repos=frozenset({"omnimarket"})))
)  # same event_id as REPO_HOLD, different scope


@pytest.mark.parametrize(
    ("lines", "reason_fragment"),
    [
        pytest.param((line(REPO_HOLD),), NO_EPOCH_REASON, id="missing-epoch"),
        pytest.param((), NO_EPOCH_REASON, id="empty-ledger"),
        pytest.param((line(epoch()), "{not json"), "does not parse", id="unparseable"),
        pytest.param((line(epoch()), ""), "does not parse", id="blank-line"),
        pytest.param(
            (line(epoch()), _UNKNOWN_KIND), "does not parse", id="unknown-kind"
        ),
        pytest.param(
            (line(epoch()), _UNKNOWN_SCHEMA), "does not parse", id="unknown-schema"
        ),
        pytest.param(
            (line(epoch()), line(REPO_HOLD), _CONFLICT),
            "conflicting duplicate event_id",
            id="conflicting-duplicate",
        ),
    ],
)
def test_undecided_never_clear(lines: tuple[str, ...], reason_fragment: str) -> None:
    state = _fold(*lines)

    assert not state.decidable
    assert any(reason_fragment in reason for reason in state.undecided_reasons)
    verdicts = _all_verdicts(state)
    assert verdicts == [S.UNDECIDED] * len(verdicts)
    assert is_held(state, INFRA_1, MERGE, runtime_affecting=True).exit_code == 2


def test_undecided_positive_control_same_lines_with_epoch_decide() -> None:
    """The unparseable-line case minus its bad line decides: the bad line was the cause."""
    state = _fold(line(epoch()), line(REPO_HOLD))

    assert state.decidable
    assert _held(state) is S.HELD


def test_identical_duplicate_counts_once() -> None:
    state = _fold(line(epoch()), line(REPO_HOLD), line(REPO_HOLD))

    assert state.decidable
    assert state.event_count == 2
    assert state.line_count == 3
    assert len(state.holds_in_force) == 1


# --------------------------------------------------------------------------- #
# AC6: the handler is pure (no envelope, no handler-output wrapper)
# --------------------------------------------------------------------------- #


def test_no_envelope_in_handler_imports() -> None:
    node_dir = Path(handler.__file__).parent
    forbidden = {"ModelEventEnvelope", "ModelHandlerOutput"}
    for module in sorted(node_dir.glob("*.py")):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        names = {
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom | ast.Import)
            for alias in node.names
        }
        assert not names & forbidden, f"{module.name} imports {names & forbidden}"


def test_no_envelope_check_positive_control() -> None:
    """The AST scan above does see a planted envelope import."""
    tree = ast.parse(
        "from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope"
    )
    names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "ModelEventEnvelope" in names


# --------------------------------------------------------------------------- #
# Releases
# --------------------------------------------------------------------------- #


def test_full_release_lifts_the_hold() -> None:
    state = _fold(line(epoch()), line(REPO_HOLD), line(release(eid(2), eid(1))))

    assert _held(state) is S.CLEAR
    assert state.holds_in_force == ()


def test_partial_release_of_one_pr_is_an_exemption_from_a_repo_pause() -> None:
    state = _fold(
        line(epoch()),
        line(REPO_HOLD),
        line(release(eid(2), eid(1), partial=ModelHoldScope(prs=frozenset({INFRA_1})))),
    )

    assert _held(state, INFRA_1) is S.CLEAR
    assert _held(state, INFRA_2) is S.HELD
    pauses = pauses_in_force(state, "omnibase_infra", runtime_affecting=True)
    assert pauses.status is S.HELD
    exemptions = pauses.holds[0].partial_releases
    assert [r.partial_scope.prs for r in exemptions if r.partial_scope] == [
        frozenset({INFRA_1})
    ]


def test_partial_releases_together_covering_the_scope_lift_the_hold() -> None:
    two_prs = hold(eid(1), ModelHoldScope(prs=frozenset({INFRA_1, MARKET_1})))
    state = _fold(
        line(epoch()),
        line(two_prs),
        line(release(eid(2), eid(1), partial=ModelHoldScope(prs=frozenset({INFRA_1})))),
        line(
            release(eid(3), eid(1), partial=ModelHoldScope(prs=frozenset({MARKET_1})))
        ),
    )

    assert state.holds_in_force == ()


def test_non_subset_partial_releases_nothing_and_is_listed() -> None:
    state = _fold(
        line(epoch()),
        line(REPO_HOLD),
        line(
            release(
                eid(2), eid(1), partial=ModelHoldScope(repos=frozenset({"omnimarket"}))
            )
        ),
    )

    assert _held(state) is S.HELD
    assert [bad.reason for bad in state.invalid_releases] == [
        EnumInvalidReleaseReason.NOT_SUBSET
    ]


def test_release_of_unknown_id_releases_nothing_and_is_listed() -> None:
    state = _fold(line(epoch()), line(REPO_HOLD), line(release(eid(2), eid(99))))

    assert _held(state) is S.HELD
    assert [bad.reason for bad in state.invalid_releases] == [
        EnumInvalidReleaseReason.UNKNOWN_HOLD
    ]


def test_release_naming_a_non_hold_is_listed() -> None:
    state = _fold(
        line(epoch()),
        line(REPO_HOLD),
        line(claim(eid(5), "OMN-1")),
        line(release(eid(2), eid(5))),
    )

    assert _held(state) is S.HELD
    assert [bad.reason for bad in state.invalid_releases] == [
        EnumInvalidReleaseReason.NOT_A_HOLD
    ]


def test_reap_of_a_hold_that_is_not_a_lease_is_listed() -> None:
    state = _fold(
        line(epoch()),
        line(REPO_HOLD),
        line(
            release(eid(2), eid(1), reap=True, surface_result=EnumSurfaceResult.ABORTED)
        ),
    )

    assert _held(state) is S.HELD
    assert [bad.reason for bad in state.invalid_releases] == [
        EnumInvalidReleaseReason.REAP_WITHOUT_LEASE
    ]


LEASE = hold(
    eid(10),
    ModelHoldScope(surfaces=frozenset({"dogfood-105"})),
    blocks=frozenset({EnumHoldBlock.DEPLOY}),
    expires_at=T0 + timedelta(minutes=30),
)


def test_surface_release_without_outcome_is_listed() -> None:
    state = _fold(line(epoch()), line(LEASE), line(release(eid(11), eid(10))))

    assert surface_lease(state, "dogfood-105").status is S.HELD
    assert [bad.reason for bad in state.invalid_releases] == [
        EnumInvalidReleaseReason.MISSING_SURFACE_RESULT
    ]


def test_expired_lease_still_blocks_until_reaped() -> None:
    later = T0 + timedelta(hours=2)
    expired = _fold(line(epoch()), line(LEASE), as_of=later)
    verdict = surface_lease(expired, "dogfood-105")

    assert verdict.status is S.HELD
    assert verdict.holds[0].expired_unreleased is True

    reaped = _fold(
        line(epoch()),
        line(LEASE),
        line(
            release(
                eid(11), eid(10), reap=True, surface_result=EnumSurfaceResult.ABORTED
            )
        ),
        as_of=later,
    )
    assert surface_lease(reaped, "dogfood-105").status is S.CLEAR


def test_unexpired_lease_is_not_marked_expired() -> None:
    state = _fold(line(epoch()), line(LEASE), as_of=T0)

    assert surface_lease(state, "dogfood-105").holds[0].expired_unreleased is False


# --------------------------------------------------------------------------- #
# Blocks and runtime class
# --------------------------------------------------------------------------- #


def test_hold_blocks_only_its_actions() -> None:
    state = _fold(line(epoch()), line(REPO_HOLD))

    assert is_held(
        state, INFRA_1, EnumHoldBlock.ARM, runtime_affecting=True
    ).status is (S.CLEAR)


def test_runtime_only_hold_skips_non_runtime_and_holds_unknown() -> None:
    runtime_hold = hold(
        eid(1), ModelHoldScope(repos=frozenset({"omnibase_infra"})), runtime_only=True
    )
    state = _fold(line(epoch()), line(runtime_hold))

    assert is_held(state, INFRA_1, MERGE, runtime_affecting=False).status is S.CLEAR
    assert is_held(state, INFRA_1, MERGE, runtime_affecting=True).status is S.HELD
    assert is_held(state, INFRA_1, MERGE, runtime_affecting=None).status is S.HELD


# --------------------------------------------------------------------------- #
# Claims
# --------------------------------------------------------------------------- #


def test_claims_open_until_released_or_closed() -> None:
    state = _fold(
        line(epoch()),
        line(claim(eid(20), "OMN-1", prs=frozenset({INFRA_1}), lane="lane-a")),
        line(claim(eid(21), "OMN-2", lane="lane-b")),
        line(claim(eid(22), "OMN-3", lane="lane-b")),
        line(claim_release(eid(23), "OMN-2", eid(21))),
        line(result(eid(24), frozenset({eid(22)}))),
    )

    assert [c.event_id for c in state.open_claims] == [eid(20)]
    assert open_claims(state, ticket_id="omn-1").status is S.FOUND
    assert open_claims(state, pr=INFRA_1).status is S.FOUND
    assert open_claims(state, lane="lane-a").status is S.FOUND
    assert open_claims(state, lane="lane-b").status is S.CLEAR
    assert open_claims(state, ticket_id="OMN-2").status is S.CLEAR
    assert open_claims(state, ticket_id="OMN-2").exit_code == 0
    assert open_claims(state, ticket_id="OMN-1").exit_code == 3


# --------------------------------------------------------------------------- #
# Inbox
# --------------------------------------------------------------------------- #


def test_inbox_holds_messages_until_the_lane_acks_them() -> None:
    to_b = message(eid(30), ModelRecipients(lanes=frozenset({"lane-b"})))
    to_all = message(eid(31), ModelRecipients(all_lanes=True))
    state = _fold(
        line(epoch()),
        line(to_b),
        line(to_all),
        line(ack(eid(32), eid(31), lane="lane-c")),
    )

    assert [m.event_id for m in inbox(state, "lane-b").messages] == [eid(30), eid(31)]
    assert [m.event_id for m in inbox(state, "lane-c").messages] == []
    assert inbox(state, "lane-c").status is S.CLEAR

    acked = _fold(
        line(epoch()),
        line(to_b),
        line(ack(eid(33), eid(30), lane="lane-b")),
    )
    assert inbox(acked, "lane-b").status is S.CLEAR


def test_inbox_lists_holds_addressed_to_or_scoped_on_the_lane() -> None:
    addressed = hold(
        eid(40),
        ModelHoldScope(repos=frozenset({"omnimarket"})),
        addressed_to=ModelRecipients(lanes=frozenset({"lane-b"})),
    )
    on_lane = hold(eid(41), ModelHoldScope(lanes=frozenset({"lane-b"})))
    state = _fold(
        line(epoch()),
        line(addressed),
        line(on_lane),
        line(ack(eid(42), eid(40), lane="lane-b")),
        line(ack(eid(43), eid(41), lane="lane-b")),
    )

    # The addressed hold is acknowledged; the hold on the lane still binds it.
    assert [h.hold.event_id for h in inbox(state, "lane-b").holds] == [eid(41)]
    assert inbox(state, "lane-b").status is S.FOUND


# --------------------------------------------------------------------------- #
# Health, and the handler equals the fold of the parsed events
# --------------------------------------------------------------------------- #


def test_health_reports_counts_epoch_and_refusals() -> None:
    state = _fold(line(epoch()), line(REPO_HOLD), line(release(eid(2), eid(99))))
    report = health(state)

    assert report.line_count == 3
    assert report.event_count == 3
    assert report.epoch_seq == 0
    assert report.epoch_event_id == epoch().event_id
    assert report.holds_in_force_count == 1
    assert report.invalid_release_count == 1
    assert report.undecided_reasons == ()


def test_handler_equals_fold_of_parsed_events() -> None:
    events: list[ModelWorkEvent] = [epoch(), REPO_HOLD, release(eid(2), eid(1))]

    assert _fold(*(line(e) for e in events)) == fold_work_events(events)


# --------------------------------------------------------------------------- #
# complete_ledger_lines: an unterminated tail is an unfinished append
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", ()),
        ("a\n", ("a",)),
        ("a\nb\n", ("a", "b")),
        ("a\nb", ("a",)),
        ("a\n\nb\n", ("a", "", "b")),
        ("partial", ()),
    ],
)
def test_complete_ledger_lines(text: str, expected: tuple[str, ...]) -> None:
    assert complete_ledger_lines(text) == expected


def test_unterminated_tail_is_ignored_not_undecided() -> None:
    text = line(epoch()) + "\n" + line(REPO_HOLD) + "\n" + line(REPO_HOLD)[:40]
    state = _fold(*complete_ledger_lines(text))

    assert state.decidable
    assert _held(state) is S.HELD
