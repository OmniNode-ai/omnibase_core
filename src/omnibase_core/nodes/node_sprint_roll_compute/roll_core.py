# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The sprint roll's placement arithmetic. Pure: no clock, no network, no filesystem.

Regenerated from the omni plugin's `sprint-roll` script (OMN-20395), which the
canonical-file-shape gate refused under the operator ruling of 2026-10-01: new
capability is a contract + node + handler, and the shrink-only baseline that
grandfathers 90 existing skill scripts cannot grow. The precedent for the migration is
`node_test_selector_compute`, which did the same for `scripts/ci/detect_test_paths.py`.
"""

from __future__ import annotations

import datetime as dt
import statistics
from uuid import UUID

from omnibase_core.enums.enum_capacity_unit import EnumCapacityUnit
from omnibase_core.models.nodes.sprint_roll.model_criterion_proposal import (
    ModelCriterionProposal,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint import ModelSprint
from omnibase_core.models.nodes.sprint_roll.model_sprint_placement import (
    ModelSprintPlacement,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_plan import (
    ModelSprintRollPlan,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_request import (
    ModelSprintRollRequest,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_ticket import ModelSprintTicket

__all__ = ["compute_roll", "propose_criterion", "resolve_source", "measure_capacity"]

#: An overlap of 8+ terms with a criterion's own wording agreed with a hand reading on
#: every one of the 17 orphans of the 2026-10-05 roll. Between 4 and 7 it was wrong four
#: times in six -- a CI-hygiene ticket landed on C30, two others on the C27
#: meta-criterion. So 8 assigns, and 4..7 reports a near miss for a human to settle.
STRONG_OVERLAP = 8
WEAK_OVERLAP = 4
#: Only words longer than this are compared; shorter ones match everything.
_MIN_TERM_LEN = 5


class SprintRollError(ValueError):
    """The window cannot be rolled, with the reason the caller should print."""


def _open_tickets(
    sprint: ModelSprint, closed_states: frozenset[str]
) -> list[ModelSprintTicket]:
    return [t for t in sprint.tickets if t.state not in closed_states]


def resolve_source(
    sprints: tuple[ModelSprint, ...], as_of: dt.date
) -> tuple[ModelSprint, tuple[ModelSprint, ...]]:
    """The sprint to drain, and the sprints after it to rebalance.

    THE SPRINT CONTAINING `as_of` IS THE ONE DRAINED. An earlier rule drained the
    containing sprint only on its LAST day and otherwise took the most recently ended
    one. That is right on a Sunday and right at 07:00 on a Monday, and wrong every other
    day: a Wednesday run re-drained the previous sprint -- already drained -- and treated
    the live sprint as a TARGET, which on the 2026-10-03 dry run moved 84 tickets INTO
    the running sprint and emptied the three after it.

    A caller that wants the sprint which just ended says so with `as_of`: the scheduled
    Monday job passes the Sunday that closed it, which lands inside that window. One rule
    covers both, and nothing is re-drained.

    When windows overlap -- the board carries some -- the containing sprint with the
    LATEST start wins, because that is the one in progress.
    """
    if not sprints:
        raise SprintRollError("no sprints were given, so there is nothing to roll")
    chron = sorted(sprints, key=lambda s: s.start)
    containing = [s for s in chron if s.start <= as_of <= s.end]
    if containing:
        source = containing[-1]
    else:
        ended = [s for s in chron if s.end < as_of]
        if not ended:
            raise SprintRollError(
                f"no sprint contains {as_of} and none ended before it, so there is "
                "nothing to roll"
            )
        source = max(ended, key=lambda s: s.end)
    index = chron.index(source)
    following = tuple(chron[index + 1 :])
    if not following:
        raise SprintRollError(
            f"no sprint follows {source.name}, so there is nowhere to roll it into"
        )
    return source, following


def median_estimate(tickets: list[ModelSprintTicket], fallback: int = 3) -> int:
    """The median of the estimates that exist, for imputing the ones that do not."""
    seen = [t.estimate for t in tickets if t.estimate]
    return round(statistics.median(seen)) if seen else fallback


def measure_capacity(
    sprint: ModelSprint,
    unit: EnumCapacityUnit,
    closed_states: frozenset[str],
    as_of: dt.date | None = None,
) -> tuple[int, str]:
    """Throughput measured on the drained sprint, in the unit in use.

    Extrapolated from the days elapsed to the span, so a sprint read mid-week does not
    understate a week. TWO CLAMPS MAKE THAT SAFE, and the second was missing: a sprint
    whose window has already closed -- its end on or before `as_of` -- counts its WHOLE
    span as elapsed. Without it the
    2026-10-03 dry run read a finished sprint as `142 tickets closed in 1 of 7 days` and
    reported a cap of 994 -- seven times a real week -- because a stale `elapsed_days`
    of 1 was multiplied by the span. `elapsed` is also never allowed to exceed the span.

    This is still a one-sprint sample and so the weakest input to the plan; a caller with
    a better figure passes `cap_override`.
    """
    done = [t for t in sprint.tickets if t.state in closed_states]
    span = sprint.span_days if sprint.span_days > 0 else 7
    if as_of is not None and sprint.end <= as_of:
        elapsed = span
    else:
        elapsed = min(max(1, sprint.elapsed_days), span)
    if unit is EnumCapacityUnit.POINTS:
        amount = sum(t.estimate or 0 for t in done)
        label = "pts"
    else:
        amount = len(done)
        label = "tickets"
    cap = round(amount / elapsed * span)
    basis = f"{amount} {label} closed in {elapsed} of {span} days"
    return max(cap, 1), basis


def _terms(text: str) -> set[str]:
    cleaned = text.lower().replace(",", " ").replace(";", " ")
    return {w for w in cleaned.split() if len(w) > _MIN_TERM_LEN}


def propose_criterion(
    description: str,
    title: str,
    criteria_text: dict[str, str],
    meta_criteria: frozenset[str] = frozenset(),
) -> ModelCriterionProposal:
    """A criterion for a ticket no carrier list names, declared basis first.

    The order is the whole point. A ticket that names its own gate is not a guess and is
    never overridden by a text match. Only when nothing is declared does this fall back
    to wording overlap, and a weak overlap assigns nothing -- it names the near miss so a
    person can settle it. The reconciliation gate forbids an allowlist, so the honest
    answer for an unmappable ticket is a recorded ruling or a dropped label, never an
    invented carrier.
    """
    body = description or ""
    for line in body.splitlines():
        if not line.strip().lower().startswith("gate:"):
            continue
        rest = line.split(":", 1)[1]
        words = set(
            rest.lower().replace("(", " ").replace(")", " ").replace(",", " ").split()
        )
        for criterion in sorted(criteria_text, key=len, reverse=True):
            if criterion.lower() in words:
                return ModelCriterionProposal(
                    identifier="",
                    criterion=criterion,
                    basis="declared in the ticket's Gate line",
                )
        break

    haystack = f"{title} {body}".lower()
    best: str | None = None
    score = 0
    for criterion, text in criteria_text.items():
        if criterion in meta_criteria:
            continue
        hit = sum(1 for term in _terms(text) if term in haystack)
        if hit > score:
            best, score = criterion, hit
    if score >= STRONG_OVERLAP:
        return ModelCriterionProposal(
            identifier="",
            criterion=best,
            basis=f"criterion text overlap ({score} terms)",
            near_miss_criterion=best,
            near_miss_score=score,
        )
    if score >= WEAK_OVERLAP:
        return ModelCriterionProposal(
            identifier="",
            criterion=None,
            basis=f"no declared gate; weak match only, suggest {best} ({score} terms)",
            near_miss_criterion=best,
            near_miss_score=score,
        )
    return ModelCriterionProposal(
        identifier="",
        criterion=None,
        basis="no declared gate and no text match",
    )


def compute_roll(request: ModelSprintRollRequest) -> ModelSprintRollPlan:
    """Place every open ticket in the window, and propose a criterion for the orphans.

    The window is rebalanced as a whole rather than injected into. An earlier version
    placed only the drained sprint's tickets and treated each later sprint's contents as
    fixed, which parks the roll behind whatever a later sprint already held: on the
    2026-10-05 window the 10-12 sprint sat at 20 of a 21 cap, so exactly one ticket could
    enter it while 21 went to the empty 10-19. The sprints after the current one are
    plans, not commitments, so every open ticket is pooled and ranked once.
    """
    source, following = resolve_source(request.sprints, request.as_of)
    closed = request.closed_states
    rolling = _open_tickets(source, closed)
    median = median_estimate(rolling)

    if request.cap_override is not None:
        cap, basis = request.cap_override, "caller override"
    else:
        cap, basis = measure_capacity(
            source, request.capacity_unit, closed, request.as_of
        )

    def size(ticket: ModelSprintTicket) -> int:
        # In ticket mode every ticket costs one, so an unestimated ticket needs no
        # imputation at all -- which is why tickets is the default unit.
        if request.capacity_unit is EnumCapacityUnit.POINTS:
            return ticket.estimate or median
        return 1

    origin: dict[str, UUID] = {t.identifier: source.sprint_id for t in rolling}
    pool: list[ModelSprintTicket] = list(rolling)
    for sprint in following:
        for ticket in _open_tickets(sprint, closed):
            if ticket.identifier in origin:
                continue
            origin[ticket.identifier] = sprint.sprint_id
            pool.append(ticket)

    default_rank = max(request.state_rank.values(), default=0) + 1
    pool.sort(
        key=lambda t: (
            request.state_rank.get(t.state, default_rank),
            0 if t.is_carrier else 1,
            0 if t.identifier in request.criteria else 1,
            -(t.estimate or 0),
            t.identifier,
        )
    )

    # Only some of the following sprints may be targets. The M4.5 bucket is a parked
    # fast-follow list, not next week's plan: left in, the 2026-10-04 run rebalanced it
    # to the cap, moving 20 tickets in and pushing 26 out of a sprint nobody was
    # planning. Its own open tickets still enter the pool, so excluding it does not
    # strand them -- they compete for a real sprint like everything else.
    targets = [
        s
        for s in following
        if not request.target_sprint_ids or s.sprint_id in request.target_sprint_ids
    ]
    if not targets:
        raise SprintRollError(
            "every sprint after the source was excluded as a target, so there is "
            "nowhere to roll it into"
        )

    load: dict[UUID, int] = {s.sprint_id: 0 for s in targets}
    by_owner: dict[UUID, dict[str, int]] = {s.sprint_id: {} for s in targets}
    placed: dict[UUID, list[ModelSprintTicket]] = {s.sprint_id: [] for s in targets}
    backlog: list[ModelSprintTicket] = []
    seated: set[str] = set()

    def owner_room(sprint_id: UUID, ticket: ModelSprintTicket) -> bool:
        """Whether this owner has room left in this sprint."""
        if request.owner_cap is None or ticket.owner is None:
            return True
        spent = by_owner[sprint_id].get(ticket.owner, 0)
        return spent + size(ticket) <= request.owner_cap

    def seat(sprint_id: UUID, ticket: ModelSprintTicket) -> None:
        placed[sprint_id].append(ticket)
        load[sprint_id] += size(ticket)
        if ticket.owner is not None:
            by_owner[sprint_id][ticket.owner] = by_owner[sprint_id].get(
                ticket.owner, 0
            ) + size(ticket)
        seated.add(ticket.identifier)

    # PASS 1 -- MANDATORY, INTO THE FIRST TARGET, CAP OR NO CAP. A walk is the only
    # evidence that someone who did not build a thing exercised it, so a cap may not
    # defer one: the 2026-10-04 run put all three delegation walks in Backlog. Their
    # size still counts, so the overflow they cause lands on ordinary work below.
    first = targets[0]
    for ticket in pool:
        if ticket.identifier in request.mandatory:
            seat(first.sprint_id, ticket)

    # PASS 2 -- PILLAR FLOOR. A sprint that ships one pillar and starves another reads
    # as progress and is not; the first cascade gave a 36-of-46-point Dashboard sprint
    # with zero Delegation. Each pillar takes its highest-ranked tickets first, within
    # the team cap and the owner cap, before the general pass claims the room.
    if request.pillar_floor > 0 and request.pillar_of:
        pillars = sorted(set(request.pillar_of.values()))
        for sprint in targets:
            for pillar in pillars:
                have = sum(
                    1
                    for t in placed[sprint.sprint_id]
                    if request.pillar_of.get(t.identifier) == pillar
                )
                for ticket in pool:
                    if have >= request.pillar_floor:
                        break
                    if ticket.identifier in seated:
                        continue
                    if request.pillar_of.get(ticket.identifier) != pillar:
                        continue
                    if load[sprint.sprint_id] + size(ticket) > cap:
                        continue
                    if not owner_room(sprint.sprint_id, ticket):
                        continue
                    seat(sprint.sprint_id, ticket)
                    have += 1

    # PASS 3 -- THE GENERAL FILL, forward through the targets.
    for ticket in pool:
        if ticket.identifier in seated:
            continue
        for sprint in targets:
            if load[sprint.sprint_id] + size(ticket) <= cap and owner_room(
                sprint.sprint_id, ticket
            ):
                seat(sprint.sprint_id, ticket)
                break
        else:
            backlog.append(ticket)

    placements = tuple(
        ModelSprintPlacement(
            sprint_id=s.sprint_id,
            name=s.name,
            load_before=sum(size(t) for t in _open_tickets(s, closed)),
            load_after=load[s.sprint_id],
            ticket_ids=tuple(t.identifier for t in placed[s.sprint_id]),
            moved_in=tuple(
                t.identifier
                for t in placed[s.sprint_id]
                if origin.get(t.identifier) != s.sprint_id
            ),
        )
        for s in targets
    )

    proposals = tuple(
        propose_criterion(
            t.description,
            t.title,
            request.criteria_text,
            request.meta_criteria,
        ).model_copy(update={"identifier": t.identifier})
        for t in pool
        if t.identifier not in request.criteria
    )

    # A BASE ESTIMATE FOR EVERY UNESTIMATED TICKET, so a sprint total is a number
    # rather than a shrug. The operator's rule for this is explicit: anyone may change
    # an estimate, so a proposed one that is roughly right beats a blank that silently
    # costs nothing. Three sizes, from the one signal available without reading the work
    # -- the median of what IS estimated, nudged by whether the ticket is a carrier
    # (criterion-bearing work runs larger) and whether it is a parent (its children hold
    # the points, so a parent proposes nothing and is reported instead). The caller
    # writes these; this node only proposes, and never overwrites an estimate that
    # exists.
    proposed = {
        t.identifier: max(1, median + 1 if t.is_carrier else median)
        for t in pool
        if not t.estimate and t.identifier not in request.parents
    }
    parents_skipped = tuple(
        sorted(
            t.identifier
            for t in pool
            if not t.estimate and t.identifier in request.parents
        )
    )

    return ModelSprintRollPlan(
        proposed_estimates=proposed,
        unestimated_parents=parents_skipped,
        source_sprint_id=source.sprint_id,
        source_sprint_name=source.name,
        cap=cap,
        cap_basis=basis,
        median_estimate=median,
        rolling_ticket_ids=tuple(t.identifier for t in rolling),
        placements=placements,
        backlog_ticket_ids=tuple(t.identifier for t in backlog),
        proposals=proposals,
    )
