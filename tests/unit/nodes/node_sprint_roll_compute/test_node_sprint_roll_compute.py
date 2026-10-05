# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Cases for the sprint_roll COMPUTE node (OMN-20396).

Ported from the omni plugin's sprint-roll suite. Every case builds its window in
memory: the node is pure, so no Linear account, no network and no omninode_infra
checkout is needed, and that is the property AC2 asserts.
"""

from __future__ import annotations

import datetime as dt
from uuid import UUID

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_capacity_unit import EnumCapacityUnit
from omnibase_core.models.nodes.sprint_roll.model_sprint import ModelSprint
from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_plan import (
    ModelSprintRollPlan,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_request import (
    ModelSprintRollRequest,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_ticket import ModelSprintTicket
from omnibase_core.nodes.node_sprint_roll_compute import NodeSprintRollCompute
from omnibase_core.nodes.node_sprint_roll_compute.roll_core import (
    SprintRollError,
    measure_capacity,
    propose_criterion,
    resolve_source,
)

C30 = (
    "A developer's first hour on a machine that is not the operator's: the public "
    "quickstart alone gets them from install to their own provider key to a Claude "
    "Code delegation, and that run's model, tokens, cost and receipt appear on a "
    "dashboard served from the machine"
)
CRITERIA_TEXT = {
    "C11": "Negative paths: wrong key, absent key, wrong tenant, malformed",
    "C27": (
        "Every gate row in section 7.1 has a ticket in the beta sprint, or a "
        "recorded ruling that retires it"
    ),
    "C30": C30,
}


def _ticket(
    identifier: str,
    state: str = "Backlog",
    estimate: int | None = None,
    carrier: bool = False,
    description: str = "",
) -> ModelSprintTicket:
    return ModelSprintTicket(
        identifier=identifier,
        state=state,
        estimate=estimate,
        is_carrier=carrier,
        owner="owner",
        title=identifier,
        description=description,
    )


#: Deterministic stand-ins for Linear project ids, so a failure names a readable
#: sprint instead of a random uuid.
P0, P1, P2, P3 = (UUID(int=n) for n in range(4))
SPRINT_NAME = {P0: "p0", P1: "p1", P2: "p2", P3: "p3"}


def _sprint(
    sprint_id: UUID,
    start: str,
    end: str,
    tickets: tuple[ModelSprintTicket, ...],
    elapsed: int = 7,
) -> ModelSprint:
    return ModelSprint(
        sprint_id=sprint_id,
        name=SPRINT_NAME[sprint_id],
        start=dt.date.fromisoformat(start),
        end=dt.date.fromisoformat(end),
        tickets=tickets,
        elapsed_days=elapsed,
        span_days=7,
    )


def _window() -> tuple[ModelSprint, ...]:
    """One sprint finishing and three plans — the shape every roll sees."""
    return (
        _sprint(
            P0,
            "2026-09-28",
            "2026-10-04",
            (
                _ticket("A1", "In Review", 2, carrier=True),
                _ticket("A2", "In Progress", 5, carrier=True),
                _ticket("A3"),
                _ticket("A4"),
                _ticket("A5"),
                _ticket("A6", "Done", 3),
            ),
        ),
        _sprint(
            P1,
            "2026-10-05",
            "2026-10-11",
            (_ticket("B1", carrier=True), _ticket("B2"), _ticket("B3")),
        ),
        _sprint(
            P2,
            "2026-10-12",
            "2026-10-18",
            (_ticket("C1"), _ticket("C2"), _ticket("C3")),
        ),
        _sprint(P3, "2026-10-19", "2026-10-25", ()),
    )


def _request(
    as_of: str = "2026-10-04",
    capacity_unit: EnumCapacityUnit = EnumCapacityUnit.TICKETS,
    cap_override: int | None = None,
    criteria: dict[str, tuple[str, ...]] | None = None,
) -> ModelSprintRollRequest:
    """Named arguments rather than kwargs, so the call site stays type-checkable."""
    return ModelSprintRollRequest(
        sprints=_window(),
        as_of=dt.date.fromisoformat(as_of),
        criteria_text=CRITERIA_TEXT,
        capacity_unit=capacity_unit,
        cap_override=cap_override,
        criteria=criteria or {},
    )


def _plan(
    as_of: str = "2026-10-04",
    capacity_unit: EnumCapacityUnit = EnumCapacityUnit.TICKETS,
    cap_override: int | None = None,
    criteria: dict[str, tuple[str, ...]] | None = None,
) -> ModelSprintRollPlan:
    return NodeSprintRollCompute().handle(
        _request(as_of, capacity_unit, cap_override, criteria)
    )


# -- which sprint is drained (AC3) --------------------------------------------


def test_a_sunday_run_drains_the_sprint_whose_last_day_it_is() -> None:
    source, following = resolve_source(_window(), dt.date(2026, 10, 4))
    assert source.sprint_id == P0
    assert [s.sprint_id for s in following] == [P1, P2, P3]


def test_a_window_with_nothing_after_the_source_is_refused() -> None:
    window = (_sprint(P0, "2026-09-28", "2026-10-04", ()),)
    with pytest.raises(SprintRollError, match="nowhere to roll"):
        resolve_source(window, dt.date(2026, 10, 4))


def test_a_date_before_every_sprint_is_refused() -> None:
    with pytest.raises(SprintRollError, match="nothing to roll"):
        resolve_source(_window(), dt.date(2026, 9, 1))


def test_an_empty_window_is_refused() -> None:
    with pytest.raises(SprintRollError, match="nothing to roll"):
        resolve_source((), dt.date(2026, 10, 4))


# -- capacity (AC5) -----------------------------------------------------------


def test_ticket_capacity_ignores_estimates_entirely() -> None:
    cap, basis = measure_capacity(
        _window()[0], EnumCapacityUnit.TICKETS, frozenset({"Done"})
    )
    assert cap == 1
    assert basis == "1 tickets closed in 7 of 7 days"


def test_points_capacity_reads_the_estimates() -> None:
    cap, _ = measure_capacity(
        _window()[0], EnumCapacityUnit.POINTS, frozenset({"Done"})
    )
    assert cap == 3


def test_a_partial_week_is_extrapolated_to_the_span() -> None:
    sprint = _sprint(
        P0, "2026-09-28", "2026-10-04", (_ticket("X", "Done", 1),), elapsed=1
    )
    assert (
        measure_capacity(sprint, EnumCapacityUnit.TICKETS, frozenset({"Done"}))[0] == 7
    )


def test_capacity_never_measures_zero() -> None:
    sprint = _sprint(P0, "2026-09-28", "2026-10-04", (_ticket("X"),))
    assert (
        measure_capacity(sprint, EnumCapacityUnit.TICKETS, frozenset({"Done"}))[0] == 1
    )


def test_an_override_replaces_the_measurement_and_says_so() -> None:
    plan = _plan(cap_override=4)
    assert plan.cap == 4
    assert plan.cap_basis == "caller override"


def test_an_unestimated_ticket_never_costs_zero_in_points_mode() -> None:
    """Counting it as zero let unestimated tickets fill a sprint for free.

    The open rolling tickets carry estimates 2 and 5, so the median is 4 and each of
    A3, A4 and A5 costs 4 rather than nothing. A 6-point sprint therefore holds A1 and
    one unestimated ticket, not A1 and all three of them.
    """
    plan = _plan(capacity_unit=EnumCapacityUnit.POINTS, cap_override=6)
    assert plan.median_estimate == 4
    first = plan.placements[0]
    assert first.load_after <= 6
    assert len(first.ticket_ids) == 2


# -- the rebalance (AC4) ------------------------------------------------------


def test_every_sprint_fills_to_the_cap_and_none_exceeds_it() -> None:
    plan = _plan(cap_override=3)
    assert [p.load_after for p in plan.placements] == [3, 3, 3]


def test_a_pre_full_later_sprint_yields_its_slots_instead_of_blocking_the_roll() -> (
    None
):
    """With later contents fixed, a sprint at cap took one ticket while an empty one
    took everything. Pooling the window is what fixed that."""
    plan = _plan(cap_override=3)
    by_id = {p.sprint_id: p for p in plan.placements}
    assert set(by_id[P1].ticket_ids) >= {"A1", "A2"}
    displaced = set(by_id[P3].ticket_ids) | set(plan.backlog_ticket_ids)
    assert displaced & {"B1", "B2", "B3", "C1", "C2", "C3"}


def test_in_review_takes_the_earliest_slot_ahead_of_in_progress() -> None:
    plan = _plan(cap_override=2)
    assert plan.placements[0].ticket_ids == ("A1", "A2")


def test_a_carrier_outranks_a_non_carrier_at_the_same_state() -> None:
    plan = _plan(cap_override=3)
    cold = [t for t in plan.placements[0].ticket_ids if t.startswith("B")]
    assert cold == ["B1"]


def test_a_ticket_already_in_its_sprint_is_not_reported_as_moved() -> None:
    plan = _plan(cap_override=21)
    by_id = {p.sprint_id: p for p in plan.placements}
    assert "B1" in by_id[P1].ticket_ids
    assert "B1" not in by_id[P1].moved_in
    assert "A1" in by_id[P1].moved_in


def test_nothing_is_lost_between_the_placements_and_the_backlog() -> None:
    plan = _plan(cap_override=1)
    placed = [t for p in plan.placements for t in p.ticket_ids]
    assert len(placed) == 3
    assert len(set(placed) & set(plan.backlog_ticket_ids)) == 0
    assert len(placed) + len(plan.backlog_ticket_ids) == 11


def test_a_closed_ticket_never_rolls() -> None:
    plan = _plan(cap_override=21)
    everywhere = {t for p in plan.placements for t in p.ticket_ids}
    assert "A6" not in everywhere
    assert "A6" not in plan.backlog_ticket_ids


def test_the_plan_is_deterministic_for_one_request() -> None:
    first, second = _plan(cap_override=3), _plan(cap_override=3)
    assert first == second


# -- criterion proposals (AC6) ------------------------------------------------


def test_a_declared_gate_line_is_not_a_guess() -> None:
    out = propose_criterion("Gate: C11\n\nbody", "t", CRITERIA_TEXT)
    assert out.criterion == "C11"
    assert "declared" in out.basis


def test_a_declared_gate_line_beats_any_text_match() -> None:
    out = propose_criterion(f"Gate: C11\n\n{C30}", "t", CRITERIA_TEXT)
    assert out.criterion == "C11"


def test_a_strong_overlap_assigns() -> None:
    out = propose_criterion(C30, "t", CRITERIA_TEXT)
    assert out.criterion == "C30"
    assert "overlap" in out.basis


def test_a_weak_overlap_assigns_nothing_and_names_the_near_miss() -> None:
    weak = (
        "the developer runs install from the public quickstart on their machine "
        "with a provider key"
    )
    out = propose_criterion(weak, "t", CRITERIA_TEXT)
    assert out.criterion is None
    assert out.near_miss_criterion == "C30"
    assert 4 <= out.near_miss_score < 8


def test_no_overlap_assigns_nothing_and_names_no_near_miss() -> None:
    out = propose_criterion("rename a column", "t", CRITERIA_TEXT)
    assert out.criterion is None
    assert out.near_miss_criterion is None


def test_the_meta_criterion_is_never_proposed_by_text() -> None:
    """C27's wording matches any ticket mentioning a gate, a ticket or a sprint."""
    desc = (
        "this adds a recorded gate row for a ticket in the beta sprint, section "
        "retires the ruling"
    )
    out = propose_criterion(
        desc, "gate ticket sprint ruling", CRITERIA_TEXT, frozenset({"C27"})
    )
    assert out.criterion != "C27"


def test_only_tickets_no_carrier_list_names_get_a_proposal() -> None:
    plan = _plan(cap_override=21, criteria={"A1": ("C30",), "B1": ("C11",)})
    proposed = {p.identifier for p in plan.proposals}
    assert "A1" not in proposed and "B1" not in proposed
    assert "A3" in proposed


# -- purity (AC2) -------------------------------------------------------------


def test_the_request_and_the_plan_are_both_frozen() -> None:
    """setattr rather than assignment: a frozen model is a runtime guarantee, and the
    assignment form would need a type-checker suppression to express."""
    request = _request()
    with pytest.raises(ValidationError):
        setattr(request, "as_of", dt.date(2026, 1, 1))
    plan = NodeSprintRollCompute().handle(request)
    with pytest.raises(ValidationError):
        setattr(plan, "cap", 99)


def test_handling_a_request_twice_does_not_mutate_it() -> None:
    request = _request(cap_override=3)
    before = request.model_dump_json()
    NodeSprintRollCompute().handle(request)
    NodeSprintRollCompute().handle(request)
    assert request.model_dump_json() == before


# -- defects the 2026-10-03 live dry run found -------------------------------


def test_the_containing_sprint_is_the_one_drained_on_any_day_inside_it() -> None:
    """The old rule drained the containing sprint only on its LAST day, so a midweek
    run re-drained the previous sprint and treated the live one as a target: 84 tickets
    moved INTO the running sprint and the three after it emptied to zero."""
    for day in ("2026-10-05", "2026-10-08", "2026-10-11"):
        source, _ = resolve_source(_window(), dt.date.fromisoformat(day))
        assert source.sprint_id == P1, day


def test_a_caller_wanting_the_closed_sprint_says_so_with_as_of() -> None:
    """How the Monday job targets the sprint that just ended: pass the Sunday that
    closed it. One rule, no special case, and nothing is re-drained."""
    source, _ = resolve_source(_window(), dt.date(2026, 10, 4))
    assert source.sprint_id == P0


def test_a_gap_between_windows_falls_back_to_the_latest_ended_sprint() -> None:
    window = (
        _sprint(P0, "2026-09-28", "2026-10-04", ()),
        _sprint(P1, "2026-10-12", "2026-10-18", ()),
    )
    source, _ = resolve_source(window, dt.date(2026, 10, 7))
    assert source.sprint_id == P0


def test_overlapping_windows_pick_the_one_that_started_most_recently() -> None:
    """The board carries overlapping windows; the in-progress one is the later start."""
    window = (
        _sprint(P0, "2026-09-14", "2026-10-10", ()),
        _sprint(P1, "2026-09-28", "2026-10-04", ()),
        _sprint(P2, "2026-10-05", "2026-10-11", ()),
    )
    source, _ = resolve_source(window, dt.date(2026, 10, 1))
    assert source.sprint_id == P1


def test_a_finished_sprint_counts_its_whole_span_however_stale_elapsed_is() -> None:
    """The 994-ticket cap: a closed sprint reported `142 closed in 1 of 7 days`, so a
    stale elapsed of 1 was multiplied by the span."""
    done = tuple(_ticket(f"D{n}", "Done", 1) for n in range(142))
    sprint = _sprint(P0, "2026-09-21", "2026-09-27", done, elapsed=1)
    cap, basis = measure_capacity(
        sprint, EnumCapacityUnit.TICKETS, frozenset({"Done"}), dt.date(2026, 10, 3)
    )
    assert cap == 142
    assert basis == "142 tickets closed in 7 of 7 days"


def test_elapsed_can_never_exceed_the_span() -> None:
    sprint = _sprint(
        P0, "2026-09-28", "2026-10-04", (_ticket("X", "Done", 1),), elapsed=99
    )
    cap, basis = measure_capacity(sprint, EnumCapacityUnit.TICKETS, frozenset({"Done"}))
    # 99 clamps DOWN to the span, so the rate is 1/7 of a week and the cap is 1 -- not
    # 1/99, which would understate, and not 7x, which was the 994 defect.
    assert cap == 1
    assert basis == "1 tickets closed in 7 of 7 days"


def test_a_sprint_ending_exactly_on_as_of_is_finished() -> None:
    """The Monday job passes the Sunday that CLOSED the sprint, so `end == as_of` is
    the normal case and must count as a full span -- with `<` it read `18 closed in 1
    of 7 days` and gave a cap of 126."""
    done = tuple(_ticket(f"D{n}", "Done", 1) for n in range(18))
    sprint = _sprint(P0, "2026-09-28", "2026-10-04", done, elapsed=1)
    cap, basis = measure_capacity(
        sprint, EnumCapacityUnit.TICKETS, frozenset({"Done"}), dt.date(2026, 10, 4)
    )
    assert cap == 18
    assert basis == "18 tickets closed in 7 of 7 days"


# --------------------------------------------------------------------------------------
# Placement policy (OMN-20395 follow-up): mandatory walks, per-owner caps, pillar floors,
# excluded targets, and proposed base estimates. Every case here was a defect in the
# 2026-10-04 live dry run, not a hypothetical.
# --------------------------------------------------------------------------------------


def _owned(identifier: str, owner: str, estimate: int, state: str = "Backlog"):
    return ModelSprintTicket(
        identifier=identifier,
        state=state,
        estimate=estimate,
        is_carrier=False,
        owner=owner,
        title=identifier,
        description="",
    )


def _owned_window(source_tickets, p1_tickets=()):
    return (
        _sprint(P0, "2026-09-28", "2026-10-04", source_tickets),
        _sprint(P1, "2026-10-05", "2026-10-11", tuple(p1_tickets)),
        _sprint(P2, "2026-10-12", "2026-10-18", ()),
    )


def _policy_plan(window, **kw) -> ModelSprintRollPlan:
    return NodeSprintRollCompute().handle(
        ModelSprintRollRequest(
            sprints=window,
            as_of=dt.date(2026, 10, 4),
            capacity_unit=EnumCapacityUnit.POINTS,
            criteria_text=CRITERIA_TEXT,
            **kw,
        )
    )


def _ids_in(plan: ModelSprintRollPlan, sprint_id: UUID) -> tuple[str, ...]:
    return next(p.ticket_ids for p in plan.placements if p.sprint_id == sprint_id)


def test_points_is_the_default_capacity_unit() -> None:
    """Carriers are fully estimated now, so a flat ticket count hides a 7-vs-1 gap."""
    assert (
        ModelSprintRollRequest(
            sprints=_window(), as_of=dt.date(2026, 10, 4)
        ).capacity_unit
        is EnumCapacityUnit.POINTS
    )


def test_a_mandatory_ticket_is_seated_in_the_first_target_past_a_full_cap() -> None:
    """The three delegation walks went to Backlog on the 2026-10-04 run. A walk is the
    only evidence someone who did not build a thing exercised it, so a cap may not
    defer one."""
    window = _owned_window(
        (
            _owned("WALK", "mike", 5),
            _owned("BUILD1", "jonah", 5, "In Review"),
            _owned("BUILD2", "jonah", 5, "In Review"),
        )
    )
    plan = _policy_plan(window, cap_override=5, mandatory=frozenset({"WALK"}))
    assert "WALK" in _ids_in(plan, P1)
    assert "WALK" not in plan.backlog_ticket_ids


def test_a_mandatory_ticket_still_spends_the_load_it_costs() -> None:
    """Exempting it from the cap would silently inflate the sprint instead; the
    overflow has to land on ordinary work."""
    window = _owned_window(
        (_owned("WALK", "mike", 5), _owned("BUILD", "jonah", 5, "In Review"))
    )
    plan = _policy_plan(window, cap_override=5, mandatory=frozenset({"WALK"}))
    first = next(p for p in plan.placements if p.sprint_id == P1)
    assert first.load_after == 5
    assert "BUILD" not in first.ticket_ids


def test_an_owner_cap_stops_one_person_carrying_a_whole_sprint() -> None:
    """The team cap alone was satisfied while 42 of 46 points sat on one owner."""
    window = _owned_window(
        (
            _owned("L1", "lakshman", 6),
            _owned("L2", "lakshman", 6),
            _owned("L3", "lakshman", 6),
            _owned("J1", "jonah", 6),
        )
    )
    plan = _policy_plan(window, cap_override=24, owner_cap=12)
    seated = _ids_in(plan, P1)
    assert sum(1 for i in seated if i.startswith("L")) == 2
    assert "J1" in seated
    assert "L3" in _ids_in(plan, P2)


def test_an_owner_with_no_owner_recorded_is_not_capped() -> None:
    """A null owner is unknown, not a person; capping it would wedge the fill."""
    unowned = ModelSprintTicket(
        identifier="U1", state="Backlog", estimate=9, owner=None, title="U1"
    )
    plan = _policy_plan(_owned_window((unowned,)), cap_override=20, owner_cap=2)
    assert "U1" in _ids_in(plan, P1)


def test_a_pillar_floor_puts_every_pillar_in_every_sprint() -> None:
    """The first cascade produced a 36-of-46-point Dashboard sprint with zero
    Delegation, and nothing refused it."""
    window = _owned_window(
        (
            _owned("D1", "lakshman", 2),
            _owned("D2", "lakshman", 2),
            _owned("D3", "lakshman", 2),
            _owned("D4", "lakshman", 2),
            _owned("G1", "jonah", 2),
            _owned("O1", "jake", 2),
        )
    )
    pillars = {
        "D1": "Dashboard",
        "D2": "Dashboard",
        "D3": "Dashboard",
        "D4": "Dashboard",
        "G1": "Delegation",
        "O1": "Onboarding",
    }
    plan = _policy_plan(window, cap_override=6, pillar_of=pillars, pillar_floor=1)
    seated = _ids_in(plan, P1)
    assert {pillars[i] for i in seated} == {"Dashboard", "Delegation", "Onboarding"}


def test_a_floor_of_zero_leaves_the_ranking_alone() -> None:
    window = _owned_window((_owned("D1", "lakshman", 2), _owned("G1", "jonah", 2)))
    plan = _policy_plan(
        window,
        cap_override=2,
        pillar_of={"D1": "Dashboard", "G1": "Delegation"},
        pillar_floor=0,
    )
    assert len(_ids_in(plan, P1)) == 1


def test_an_excluded_target_receives_nothing_but_still_yields_its_tickets() -> None:
    """M4.5 is a parked fast-follow list. Left in, the run rebalanced it to the cap,
    moving 20 tickets into a sprint nobody was planning and pushing 26 out."""
    window = _owned_window(
        (_owned("A1", "jake", 2),), p1_tickets=(_owned("M45", "jonah", 2),)
    )
    plan = _policy_plan(window, cap_override=10, target_sprint_ids=frozenset({P2}))
    assert [p.sprint_id for p in plan.placements] == [P2]
    # Its own open ticket is not stranded: it competes for a real sprint.
    assert "M45" in _ids_in(plan, P2)


def test_excluding_every_target_is_refused_rather_than_silently_empty() -> None:
    window = _owned_window((_owned("A1", "jake", 2),))
    with pytest.raises(SprintRollError, match="nowhere to roll"):
        _policy_plan(window, cap_override=10, target_sprint_ids=frozenset({P0}))


def test_an_unestimated_ticket_gets_a_base_estimate() -> None:
    """Anyone may change an estimate, so a proposal that is roughly right beats a blank
    that silently costs nothing in points mode."""
    window = _owned_window(
        (
            _owned("E4", "jake", 4),
            _owned("E6", "jake", 6),
            _ticket("BLANK"),
            _ticket("BLANK_CARRIER", carrier=True),
        )
    )
    plan = _policy_plan(window, cap_override=40)
    assert plan.proposed_estimates["BLANK"] == plan.median_estimate
    assert plan.proposed_estimates["BLANK_CARRIER"] == plan.median_estimate + 1
    assert "E4" not in plan.proposed_estimates


def test_a_parent_is_reported_rather_than_estimated() -> None:
    """Estimating a parent AND its children double-counts the work."""
    window = _owned_window((_ticket("PARENT"), _ticket("LEAF")))
    plan = _policy_plan(window, cap_override=40, parents=frozenset({"PARENT"}))
    assert "PARENT" not in plan.proposed_estimates
    assert plan.unestimated_parents == ("PARENT",)
    assert "LEAF" in plan.proposed_estimates
