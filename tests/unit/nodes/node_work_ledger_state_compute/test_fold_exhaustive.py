# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Exhaustive finite check of the hold fold against a reference (OMN-19405, T4 AC2).

Universe: two repos (``ra``, ``rb``), two named PRs (``ra#1``, ``rb#1``), one
surface and one lane. For every hold scope over that universe, both values of
``runtime_only``, every sequence of up to two releases (full, unknown id, or
one of several partial scopes, each a subset or not depending on the hold),
every query PR, every ``runtime_affecting`` in {True, False, None} and each of
the four actions, the production fold plus ``is_held`` must give the same
answer as the reference below.

The reference is written separately and differently: it enumerates the PRs a
scope covers over an explicit finite target set, and releases by plain set
difference. Its target set includes an unnamed PR in each named repo and a PR
in a third repo, so repo-level and all-repo coverage stay distinguishable from
named-PR coverage. A planted bug in the reference must be caught (mutation
control), which proves the comparison can fail.
"""

from __future__ import annotations

import itertools
import uuid
from collections.abc import Iterator

import pytest

from omnibase_core.enums.enum_hold_block import EnumHoldBlock
from omnibase_core.enums.enum_surface_result import EnumSurfaceResult
from omnibase_core.enums.enum_work_ledger_verdict_status import (
    EnumWorkLedgerVerdictStatus,
)
from omnibase_core.models.events.work import (
    ModelHoldScope,
    ModelPrKey,
    ModelWorkHoldPlaced,
    ModelWorkHoldReleased,
)
from omnibase_core.nodes.node_work_ledger_state_compute.handler import (
    fold_work_events,
)
from omnibase_core.nodes.node_work_ledger_state_compute.queries import is_held

from .work_ledger_events import eid, epoch, hold, pr, release

pytestmark = pytest.mark.unit

HOLD_ID = eid(1)
UNKNOWN_ID = eid(9999)
BLOCKS = frozenset({EnumHoldBlock.MERGE, EnumHoldBlock.DEPLOY})
NAMED_PRS = (pr("ra", 1), pr("rb", 1))
QUERY_PRS = (pr("ra", 1), pr("ra", 2), pr("rb", 1), pr("rc", 1))
RUNTIME_VALUES = (True, False, None)
MIN_CASES = 100_000

# A scope spec is plain data: (prs, repos, all_repos, surfaces, lanes).
Spec = tuple[
    frozenset[ModelPrKey], frozenset[str], bool, frozenset[str], frozenset[str]
]


def _subsets[T](items: tuple[T, ...]) -> list[frozenset[T]]:
    return [
        frozenset(combo)
        for size in range(len(items) + 1)
        for combo in itertools.combinations(items, size)
    ]


def _hold_specs() -> list[Spec]:
    repo_parts: list[tuple[frozenset[str], bool]] = [
        (frozenset(repos), False) for repos in _subsets(("ra", "rb"))
    ] + [(frozenset(), True)]
    specs: list[Spec] = []
    for prs in _subsets(NAMED_PRS):
        for repos, all_repos in repo_parts:
            for surfaces in _subsets(("s",)):
                for lanes in _subsets(("l",)):
                    if prs or repos or all_repos or surfaces or lanes:
                        specs.append((prs, repos, all_repos, surfaces, lanes))
    return specs


PARTIAL_SPECS: tuple[Spec, ...] = (
    (frozenset({pr("ra", 1)}), frozenset(), False, frozenset(), frozenset()),
    (frozenset({pr("rb", 1)}), frozenset(), False, frozenset(), frozenset()),
    (frozenset({pr("ra", 2)}), frozenset(), False, frozenset(), frozenset()),
    (frozenset(), frozenset({"ra"}), False, frozenset(), frozenset()),
    (frozenset(), frozenset({"rb"}), False, frozenset(), frozenset()),
    (frozenset(), frozenset({"ra", "rb"}), False, frozenset(), frozenset()),
    (frozenset(), frozenset(), True, frozenset(), frozenset()),
    (frozenset(), frozenset(), False, frozenset({"s"}), frozenset()),
    (frozenset(), frozenset(), False, frozenset(), frozenset({"l"})),
)
FULL = "full"
UNKNOWN = "unknown"
ReleaseOption = str | Spec
RELEASE_OPTIONS: tuple[ReleaseOption, ...] = (FULL, UNKNOWN, *PARTIAL_SPECS)


def _scope(spec: Spec) -> ModelHoldScope:
    prs, repos, all_repos, surfaces, lanes = spec
    return ModelHoldScope(
        prs=prs, repos=repos, all_repos=all_repos, surfaces=surfaces, lanes=lanes
    )


# --------------------------------------------------------------------------- #
# The reference fold: explicit target sets and set difference.
# --------------------------------------------------------------------------- #

TARGETS = frozenset(
    [("pr", p.repo, p.number) for p in QUERY_PRS]
    + [("pr", "rb", 2), ("surface", "s", 0), ("lane", "l", 0)]
)


def ref_cover(spec: Spec) -> frozenset[tuple[str, str, int]]:
    prs, repos, all_repos, surfaces, lanes = spec
    return frozenset(
        t
        for t in TARGETS
        if (t[0] == "pr" and (all_repos or t[1] in repos or pr(t[1], t[2]) in prs))
        or (t[0] == "surface" and t[1] in surfaces)
        or (t[0] == "lane" and t[1] in lanes)
    )


def ref_is_held(
    hold_spec: Spec,
    runtime_only: bool,
    releases: tuple[ReleaseOption, ...],
    query: ModelPrKey,
    action: EnumHoldBlock,
    runtime_affecting: bool | None,
    *,
    planted_bug: bool = False,
) -> bool:
    if action not in BLOCKS or (runtime_only and runtime_affecting is False):
        return False
    covered = ref_cover(hold_spec)
    remaining = set(covered)
    for option in releases:
        if isinstance(option, str):
            if option == FULL:
                remaining.clear()
            continue  # UNKNOWN names no hold and releases nothing
        part = ref_cover(option)
        if not planted_bug and not part <= covered:
            continue  # a partial reaching outside the hold releases nothing
        remaining -= part
    return ("pr", query.repo, query.number) in remaining


# --------------------------------------------------------------------------- #
# Case generation and comparison
# --------------------------------------------------------------------------- #


def _release_event(
    slot: int, index: int, option: ReleaseOption
) -> ModelWorkHoldReleased:
    return release(
        eid(1000 + 100 * slot + index),
        UNKNOWN_ID if option == UNKNOWN else HOLD_ID,
        partial=None if isinstance(option, str) else _scope(option),
        surface_result=EnumSurfaceResult.PASS,
    )


RELEASE_EVENTS = {
    (slot, index): _release_event(slot, index, option)
    for slot in (0, 1)
    for index, option in enumerate(RELEASE_OPTIONS)
}


def _sequences() -> Iterator[tuple[int, ...]]:
    count = len(RELEASE_OPTIONS)
    yield ()
    for first in range(count):
        yield (first,)
    for first, second in itertools.product(range(count), repeat=2):
        yield (first, second)


Case = tuple[
    Spec, bool, tuple[ReleaseOption, ...], ModelPrKey, EnumHoldBlock, bool | None
]


def _compare(*, planted_bug: bool) -> tuple[int, list[Case]]:
    """Return the case count and the mismatches (stops at the first under a planted bug)."""
    epoch_event = epoch()
    cases = 0
    mismatches: list[Case] = []
    for hold_spec in _hold_specs():
        for runtime_only in (False, True):
            hold_event: ModelWorkHoldPlaced = hold(
                HOLD_ID, _scope(hold_spec), blocks=BLOCKS, runtime_only=runtime_only
            )
            for sequence in _sequences():
                options = tuple(RELEASE_OPTIONS[index] for index in sequence)
                releases = [
                    RELEASE_EVENTS[(slot, index)] for slot, index in enumerate(sequence)
                ]
                state = fold_work_events([epoch_event, hold_event, *releases])
                for query, action, runtime in itertools.product(
                    QUERY_PRS, EnumHoldBlock, RUNTIME_VALUES
                ):
                    cases += 1
                    verdict = is_held(state, query, action, runtime)
                    produced = verdict.status is EnumWorkLedgerVerdictStatus.HELD
                    if produced:
                        assert [h.hold.event_id for h in verdict.holds] == [HOLD_ID]
                    expected = ref_is_held(
                        hold_spec,
                        runtime_only,
                        options,
                        query,
                        action,
                        runtime,
                        planted_bug=planted_bug,
                    )
                    if produced != expected:
                        mismatches.append(
                            (hold_spec, runtime_only, options, query, action, runtime)
                        )
                        if planted_bug:
                            return cases, mismatches
    return cases, mismatches


@pytest.mark.slow
@pytest.mark.timeout(300)
def test_fold_equals_reference_over_the_finite_universe() -> None:
    cases, mismatches = _compare(planted_bug=False)

    print(f"exhaustive hold-fold cases: {cases}")
    assert cases >= MIN_CASES
    assert mismatches == [], f"{len(mismatches)} mismatches, first: {mismatches[:3]}"


def test_planted_reference_bug_is_caught() -> None:
    """Mutation control: a reference that honours non-subset partials disagrees."""
    _, mismatches = _compare(planted_bug=True)

    assert mismatches, "the comparison could not detect a planted bug"


def test_universe_is_what_the_plan_names() -> None:
    assert len({p.repo for p in NAMED_PRS}) == 2
    assert len(NAMED_PRS) == 2
    assert len(_hold_specs()) == 4 * 5 * 2 * 2 - 1
    assert uuid.UUID(str(HOLD_ID)) != UNKNOWN_ID
