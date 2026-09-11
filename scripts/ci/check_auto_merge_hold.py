#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Respect a human's auto-merge decision before re-arming (OMN-18179).

Why this exists
----------------
`auto-merge.yml`'s "Enable Auto-Merge" job arms GitHub native auto-merge
with no check for whether somebody already turned it off. The job fires on
`pull_request: opened`, and again on `pull_request_review` and
`check_suite: completed` in the repos where those events are delivered, so
an explicit `gh pr merge --disable-auto` can be undone by the next trigger
and the PR merges the moment its checks go green. Converting the PR to
draft was the only durable pause available.

Three instances inside 24 hours, all read back live from the GraphQL
timeline:

* `omninode_infra#1310` -- a prod scale-down manifest taking 13 Deployments
  to zero replicas -- armed 2026-09-10T17:15:29Z on open, disabled
  18:50:55Z, and had to be converted to draft at 18:52:35Z to contain it.
* `omninode_infra#1313` armed 22:48:54Z, disabled 22:50:41Z.
* `omnibase_core#1678` armed 10:40:33Z on open, before the authorization
  ruling for that change had reached the lane.

The rule this module implements is deliberately small: **the most recent
human decision wins.** If the latest auto-merge state-change event on the
PR is a disable, do not re-arm. Re-arming by hand writes a fresh enable
event after that disable, so automation resumes with no special case and no
label to clean up. A PR can also be held pre-emptively -- before any arming
has happened at all, which is the `#1678` shape -- by applying the
deliberate-pause label named in `HOLD_LABELS`.

Two GitHub API details this depends on, both measured 2026-09-11
---------------------------------------------------------------
1. **The enable event is not always `AutoMergeEnabledEvent`.** Arming with
   an explicit method (`gh pr merge --auto --squash`, which is what every
   no-queue repo in this org uses) emits `AutoSquashEnabledEvent`. A
   detector matching only `AutoMergeEnabledEvent` sees an empty enable
   history and misreads every squash-armed PR. All three enable variants
   are in `ENABLE_EVENT_TYPES`, and the workflow's GraphQL `itemTypes`
   filter must list the same three.

       omninode_infra#1310 ->
         AutoSquashEnabledEvent   2026-09-10T17:15:29Z jonahgabriel
         AutoMergeDisabledEvent   2026-09-10T18:50:55Z jonahgabriel
                                  reason "Manually disabled by user"

2. **`timelineItems.totalCount` ignores the `itemTypes` filter.** The same
   query that returned 2 filtered nodes for `#1310` reported
   `totalCount: 7`, and 2 nodes / `totalCount: 13` for `#1313` -- the
   unfiltered timeline length in both cases. Only `nodes` may be read. The
   workflow does not pass a count to this module at all, which is the point.

Fail-closed semantics
----------------------
Every form of "we don't know" resolves to HOLD, because an undetermined
timeline and a genuinely never-armed PR are indistinguishable from here and
must not be conflated:

* timeline undetermined (API error, unparseable, flag omitted) -> HOLD
* label set undetermined -> HOLD
* a relevant event carries no usable `createdAt`, so the events cannot be
  ordered -> HOLD
* an event type appears that is in neither `ENABLE_EVENT_TYPES` nor
  `DISABLE_EVENT_TYPES` -> HOLD. Unknown types cannot reach this module
  unless the workflow's `itemTypes` filter was widened without updating
  these tuples, and silently ignoring one would mean arming over a decision
  this module could not read.

A disable is honoured whatever its `reason`. GitHub also disables
auto-merge on its own (for example when the base branch changes), and
holding on those too is the conservative direction: the cost of an
unnecessary hold is one manual merge, while the cost of a missed hold is an
unintended merge of whatever the PR happens to contain.

This module performs **no** network I/O. The workflow fetches the timeline
and labels with `gh api` and passes them in; this module only classifies --
the same separation of concerns as `scripts/ci/merge_queue_enqueue.py`
(OMN-13214) and `check_governance_paths.py` (OMN-16117).

Usage
-----
    # Latest event is an enable -- safe to arm:
    python3 scripts/ci/check_auto_merge_hold.py hold \
        --timeline-json '[{"__typename":"AutoSquashEnabledEvent",
                           "createdAt":"2026-09-10T17:15:29Z"}]' \
        --labels-json '[]'

    # Latest event is a disable -- hold:
    python3 scripts/ci/check_auto_merge_hold.py hold \
        --timeline-json '[{"__typename":"AutoSquashEnabledEvent",
                           "createdAt":"2026-09-10T17:15:29Z"},
                          {"__typename":"AutoMergeDisabledEvent",
                           "createdAt":"2026-09-10T18:50:55Z"}]' \
        --labels-json '[]'

    # Timeline could not be resolved -- hold (fail closed):
    python3 scripts/ci/check_auto_merge_hold.py hold \
        --timeline-json 'null' --labels-json '[]'

Exit status
-----------
Always 0 on a successful classification; the verdict is the single word
written to stdout, either ``hold`` or ``arm``. A non-zero exit means this
module itself failed, which under the workflow's `set -euo pipefail` aborts
the step and therefore also declines to arm -- fail closed by construction.
Deliberately unlike `check_governance_paths.py`, which exits 1 to signal its
own "exclude" verdict and so reds the job it is only trying to skip a step
in.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

# ---------------------------------------------------------------------------
# Policy constants. The two event tuples must stay in lockstep with the
# `itemTypes` filter in auto-merge.yml's GraphQL query: an event type present
# in the query but missing here is an unknown type and fails closed (which is
# loud), while one present here but missing from the query is simply never
# delivered (which is silent, and is the failure this module is guarding).
# ---------------------------------------------------------------------------

ENABLE_EVENT_TYPES: tuple[str, ...] = (
    "AutoMergeEnabledEvent",
    "AutoSquashEnabledEvent",
    "AutoRebaseEnabledEvent",
)

DISABLE_EVENT_TYPES: tuple[str, ...] = ("AutoMergeDisabledEvent",)

HOLD_LABELS: tuple[str, ...] = ("hold:auto-merge",)

_VERDICT_HOLD = "hold"
_VERDICT_ARM = "arm"


# ---------------------------------------------------------------------------
# Pure decision logic — no I/O, directly unit-testable.
# ---------------------------------------------------------------------------


def _event_sort_key(event: dict[str, Any]) -> str:
    """Return the ISO-8601 `createdAt` an event is ordered by.

    Raises ``ValueError`` when the value is missing or not a non-empty
    string, because two auto-merge events that cannot be ordered relative to
    each other cannot answer "which decision was most recent".
    """
    created_at = event.get("createdAt")
    if not isinstance(created_at, str) or created_at.strip() == "":
        msg = f"auto-merge timeline event has no usable createdAt: {event!r}"
        raise ValueError(msg)
    return created_at


def latest_auto_merge_decision(
    timeline: Sequence[dict[str, Any]] | None,
) -> str | None:
    """Return ``"enable"``, ``"disable"``, or ``None`` for no decision yet.

    ``timeline`` is the ``nodes`` list of the PR's auto-merge timeline
    items, already filtered by the caller's ``itemTypes`` query, or ``None``
    when it could not be resolved. ``None`` is NOT the same as an empty list:
    an empty list means the query succeeded and the PR has genuinely never
    been armed or disabled.

    Raises ``ValueError`` on an unknown event type or an unorderable event.
    """
    if timeline is None:
        msg = "timeline is undetermined"
        raise ValueError(msg)

    decisions: list[tuple[str, str]] = []
    for event in timeline:
        typename = event.get("__typename")
        if typename in ENABLE_EVENT_TYPES:
            decisions.append((_event_sort_key(event), "enable"))
        elif typename in DISABLE_EVENT_TYPES:
            decisions.append((_event_sort_key(event), "disable"))
        else:
            msg = (
                f"unknown auto-merge timeline event type {typename!r}; "
                "ENABLE_EVENT_TYPES/DISABLE_EVENT_TYPES and the workflow's "
                "GraphQL itemTypes filter have drifted apart"
            )
            raise ValueError(msg)

    if not decisions:
        return None

    # ISO-8601 UTC timestamps from the GitHub API sort correctly as strings.
    decisions.sort(key=lambda pair: pair[0])
    return decisions[-1][1]


def should_hold(
    timeline: Sequence[dict[str, Any]] | None,
    labels: Sequence[str] | None,
) -> bool:
    """Decide whether auto-merge arming must be skipped for this PR.

    Returns ``True`` (hold) when the deliberate-pause label is present, when
    the most recent auto-merge decision on the PR was a disable, or when
    either input is undetermined or unreadable.
    """
    if labels is None:
        return True
    if any(_normalize_label(label) in HOLD_LABELS for label in labels):
        return True

    try:
        decision = latest_auto_merge_decision(timeline)
    except ValueError:
        return True

    return decision == "disable"


def _normalize_label(label: str) -> str:
    return label.strip().lower()


# ---------------------------------------------------------------------------
# CLI surface — the workflow shells out to this.
# ---------------------------------------------------------------------------


def _load_json_list(raw: str | None, what: str) -> list[Any] | None:
    """Parse a CLI JSON value into a resolved list, or ``None`` if undetermined.

    ``raw`` is the JSON text the workflow captured from ``gh api``, the
    literal string ``"null"`` when its own fetch failed, or ``None``/empty
    when the flag was omitted. Every one of those collapses to ``None``
    rather than being silently treated as an empty (and therefore
    permissive) list.
    """
    if raw is None or raw.strip() == "":
        return None

    parsed = json.loads(raw)  # raises json.JSONDecodeError on malformed input
    if parsed is None:
        return None
    if not isinstance(parsed, list):
        msg = f"{what} must be a JSON array or the literal null"
        raise TypeError(msg)
    return parsed


def _load_timeline(raw: str | None) -> list[dict[str, Any]] | None:
    parsed = _load_json_list(raw, "timeline-json")
    if parsed is None:
        return None
    for item in parsed:
        if not isinstance(item, dict):
            msg = "timeline-json entries must be JSON objects"
            raise TypeError(msg)
    return parsed


def _load_labels(raw: str | None) -> list[str] | None:
    parsed = _load_json_list(raw, "labels-json")
    if parsed is None:
        return None
    return [str(item) for item in parsed]


def main(argv: list[str] | None = None) -> int:
    """CLI surface for the workflow.

    Subcommand:
        hold --timeline-json <json|null> --labels-json <json|null>
            Prints ``hold`` or ``arm``. Exits 0 either way.
    """
    parser = argparse.ArgumentParser(
        description="Auto-merge arming hold check (OMN-18179)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_hold = sub.add_parser(
        "hold", help="Decide whether auto-merge arming must be skipped"
    )
    p_hold.add_argument(
        "--timeline-json",
        default=None,
        help=(
            "JSON array of the PR's auto-merge timeline item nodes, or the "
            "literal 'null' (or omit this flag) when the timeline could not "
            "be resolved -- fails closed to 'hold'."
        ),
    )
    p_hold.add_argument(
        "--labels-json",
        default=None,
        help=(
            "JSON array of the PR's label names, or the literal 'null' (or "
            "omit this flag) when the labels could not be resolved -- fails "
            "closed to 'hold'."
        ),
    )

    args = parser.parse_args(argv)

    if args.command == "hold":
        try:
            timeline = _load_timeline(args.timeline_json)
            labels = _load_labels(args.labels_json)
        except (json.JSONDecodeError, TypeError) as exc:
            sys.stderr.write(f"could not parse auto-merge inputs: {exc}; holding\n")
            sys.stdout.write(f"{_VERDICT_HOLD}\n")
            return 0

        verdict = _VERDICT_HOLD if should_hold(timeline, labels) else _VERDICT_ARM
        sys.stdout.write(f"{verdict}\n")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
