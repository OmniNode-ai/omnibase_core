# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Fail-closed verdict for the ``CI Summary`` required-context poller (OMN-14127).

Why this exists
---------------
``CI Summary`` is a required branch-protection context on omnibase_core's ``dev``
and ``main`` branches. It used to be a ``needs``-gated aggregator job
(``needs: [quality-gate, tests-gate, contract-compliance, boundary-validation]``,
all self-hosted leaves). A ``needs``-gated job gets **no** GitHub check-run until
its ``needs`` reach a terminal state, so under self-hosted runner-fleet
saturation the gate jobs never terminalized and ``CI Summary`` was **absent** —
the PR wedged ``BLOCKED`` forever with no auto-recovery. This is structurally
identical to the omniclaude wedge fixed in omniclaude #1870, ported here.

The ``ci-summary`` workflow job is now a NO-``needs``, GitHub-hosted poller: its
check-run instantiates immediately (so the required context can never be
absent), and it calls this module in a loop against the current run's job list
until a terminal verdict is reached (or a bounded deadline fires → fail-closed).

Verdict policy — DEFAULT-DENY, FAIL-CLOSED
------------------------------------------
Two independent checks; both must be satisfied for success:

1. **Default-deny failure sweep.** Any job in the run that is *present*,
   *completed*, and whose conclusion is not ``success``/``skipped`` fails the
   gate — UNLESS it is the poller itself or one of a small, explicit
   :data:`SOFT_ALLOWLIST` of jobs that already exist in ``ci.yml`` as
   non-gating (advisory / orphan). This can only ever be *stricter* than the old
   mechanism, never a rubber-stamp.

2. **Completeness anchor.** Success additionally requires that every
   :data:`GATE_JOBS` aggregate gate is *present and completed* with a
   ``success``/``skipped`` conclusion. ``quality-gate`` and ``tests-gate`` are
   themselves ``if: always()`` fail-closed aggregators over all substantive leaf
   jobs, so requiring them present+good proves the whole substantive matrix
   actually ran and passed. ``contract-compliance`` (Contract Compliance Check)
   and ``boundary-validation`` (Cross-repo boundary validation) are the two
   remaining leaves the old needs-based summary depended on. This is what
   prevents a *false green* before late-created jobs (``detect-changes`` →
   ``test-parallel`` → ``*-gate``) have even been instantiated: a pure "all
   currently-present jobs passed" check would go green too early.

If a gate is missing or still running, the verdict is PENDING (poll again). At
the caller's deadline, PENDING is converted to FAILURE (fail-closed): the
required context always reaches a terminal state.

Exit codes: ``0`` success, ``1`` failure, ``2`` pending.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime

# The poller's own job — excluded to avoid self-deadlock.
SELF_JOB_NAME = "CI Summary"

# Aggregate gate jobs that must all be present + completed + good for success.
# These are the exact set the old needs-based ``ci-summary`` depended on
# (``needs: [quality-gate, tests-gate, contract-compliance, boundary-validation]``);
# ``quality-gate`` and ``tests-gate`` are ``if: always()`` fail-closed aggregators
# over their leaf jobs. Names are the ``name:`` fields from ci.yml (NOT the job
# keys) because the GitHub jobs API reports the display name.
GATE_JOBS: tuple[str, ...] = (
    "Quality Gate",  # quality-gate: aggregates all Phase-1 quality leaves
    "Tests Gate",  # tests-gate: aggregates test-parallel + tests-integration
    "Contract Compliance Check",  # contract-compliance job (NOT "Contract Compliance")
    "Cross-repo boundary validation",  # boundary-validation job
    "OCC Companion Merged Gate (OMN-15214)",  # occ-companion-merged — cited OCC evidence must be MERGED before product merge (OMN-15222 port)
    # OMN-18031: the per-run runner routing decision (ci.yml `route`, a `uses:`
    # job, so the jobs API reports it as "<caller display name> / <inner job
    # name>"). THIS LINE IS HALF THE MECHANISM, on the identical reasoning as
    # the companion-merged entry above: the default-deny sweep below already
    # fails when a present job FAILS, but an unregistered job that is `skipped`
    # or ABSENT yields SUCCESS. Without this entry, deleting `route` from
    # ci.yml would silently retire per-run routing on a fully green run — and
    # because routing is deliberately INERT while this repo's trusted seam
    # reads '["ubuntu-latest"]', nothing about job PLACEMENT would change to
    # reveal it. That is the exact silent-retirement shape this tuple exists
    # for, and it is worse here than elsewhere: the only observable difference
    # between "routing works and chose hosted" and "routing is gone" is a
    # decision artifact nobody is required to read. The job is unconditional in
    # ci.yml (no `needs:`, no `if:`), so a skip is anomalous and never a
    # legitimate opt-out — hence the paired STRICT_SUCCESS_JOBS entry below.
    # Renaming either half of the name string breaks this registration.
    "Runner Route (OMN-18031) / route",
    # OMN-18790: the skip-count baseline ratchet (epic OMN-18775, ported from
    # omnibase_infra's OMN-18776). THIS LINE IS HALF THE MECHANISM, on the
    # identical reasoning as the two entries above: the default-deny sweep below
    # already fails CI Summary when a present job FAILS, but an unregistered job
    # that is `skipped` or ABSENT yields SUCCESS. The failure mode it closes is
    # itself silent and measured -- this repo's integration matrix skipped the
    # same 17 tests and its unit matrix the same 60, byte-identical id sets
    # across five consecutive runs on 2026-09-18 -- so a gate that could be
    # silently deleted would reproduce the exact shape it exists to refuse. The
    # job is unconditional in ci.yml (`if: always()`), so a skip is anomalous
    # and never a legitimate opt-out -- hence the paired STRICT_SUCCESS_JOBS
    # entry below. It is deliberately NOT a raw branch-protection context:
    # adding one would block every in-flight PR whose run predates the job, and
    # this registration is enforcement-equivalent. Renaming the string breaks
    # the registration. Pinned by tests/ci/test_skip_count_ratchet_omn18790.py.
    "Skip Count Ratchet (OMN-18776)",  # skip-count-ratchet
    # OMN-18865: the pre-merge wheel content-parity gate (ci.yml
    # `wheel-content-parity`). It is an ORDINARY job running a pinned
    # composite action, NOT a `uses:` job, so the jobs API reports its own
    # display name as a SINGLE segment -- unlike the `route` entry above,
    # which is a reusable and therefore reads as "<caller> / <inner job>".
    #
    # THE STRING MUST BE THE CHECK-RUN NAME, and this repository's own suite
    # cannot tell you when it is not. The tests here compare this tuple
    # against ci.yml and against the committed snapshot; neither knows what
    # GitHub will actually name the run. A stale " / wheel-content-parity"
    # suffix survived here from an earlier reusable-workflow design of this
    # same gate and passed all 64 tests. It was caught only by reading the
    # live check-run name off an open pull request, which is the one thing
    # that can catch it, and had it merged the poller would have waited for a
    # context nothing mints and wedged `dev` at the deadline. Verify against a
    # live run before changing this string.
    #
    # Registered on the identical reasoning as the `route` entry above: the
    # default-deny sweep already fails when a present job FAILS, but an
    # unregistered job that is `skipped` or ABSENT yields SUCCESS -- so
    # without this entry, deleting it from ci.yml would silently retire the
    # proof on a fully green run.
    "Wheel Content Parity (OMN-18865)",
)

# OMN-15222 (port of the omnibase_infra OMN-15214 canary, mirroring omniclaude's
# OMN-14350 STRICT_SUCCESS_JOBS precedent): jobs that must be EXACTLY
# ``success`` — stricter than GATE_JOBS membership, whose completeness anchor
# accepts ``success``||``skipped``. Each of these runs UNCONDITIONALLY in ci.yml
# (no ``if:``, no ``needs:``), so a SKIPPED or CANCELLED conclusion is anomalous
# un-enforcement and must fail closed, not pass.
STRICT_SUCCESS_JOBS: frozenset[str] = frozenset(
    {
        # OMN-18865: paired with the GATE_JOBS entry above, same reasoning --
        # GATE_JOBS' completeness anchor accepts ``skipped`` as complete, so
        # this is the half that makes a SKIPPED (or CANCELLED) parity job fail
        # closed rather than pass. The job carries no `if:` and no `needs:`,
        # so it always runs to a terminal conclusion and a `skipped` here is a
        # failure-to-run, never a legitimate absence.
        "Wheel Content Parity (OMN-18865)",
        "OCC Companion Merged Gate (OMN-15214)",
        # OMN-18031: paired with the GATE_JOBS entry above. GATE_JOBS' anchor
        # accepts ``skipped`` as complete, so this is the half that makes a
        # SKIPPED (or CANCELLED) route job fail closed rather than pass.
        "Runner Route (OMN-18031) / route",
        # OMN-18790: paired with the GATE_JOBS entry above, same reasoning --
        # GATE_JOBS' completeness anchor accepts ``skipped`` as complete, so
        # this is the half that makes a SKIPPED (or CANCELLED) ratchet job fail
        # closed rather than pass. The job is `if: always()` in ci.yml and
        # decides internally whether there is a run to ratchet, so it reaches
        # `success` even on a docs-only diff; a `skipped` conclusion means the
        # job was removed or wedged, never that the check legitimately opted
        # out.
        "Skip Count Ratchet (OMN-18776)",
    }
)

# Jobs that do NOT gate merge today (verified against ci.yml ``needs`` graph on
# 2026-07-07). The default-deny sweep ignores these so it never newly-wedges a
# PR on a job that is already non-blocking. Keep this list SMALL and only add
# jobs that genuinely already exist in ci.yml as non-gating:
#   - "Version Pin Compliance" (version-pin-check): carries
#     ``continue-on-error: true`` and is explicitly NOT a ``quality-gate`` need
#     (see the OMN-13574 comment on quality-gate ``needs``) — advisory only.
#   - "Contract Compliance" (compliance): an ORPHAN job — not in any ``needs:``
#     and not a required branch-protection context. The REAL gating contract
#     check is "Contract Compliance Check" (in GATE_JOBS above); the two names
#     are distinct and matched exactly, so allowlisting the orphan does not
#     weaken the gate.
SOFT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "Version Pin Compliance",  # version-pin-check: continue-on-error advisory
        "Contract Compliance",  # compliance: orphan job, not gated, not required
    }
)

# L4: EXPECTED_EXTERNAL_CONTEXTS (enforce-everything gate audit, four-layer
# doctrine). Every job so far (GATE_JOBS / STRICT_SUCCESS_JOBS /
# SPEC_REQUIRED_VALIDATOR_JOBS / SOFT_ALLOWLIST) lives INSIDE ci.yml's own
# workflow run and is visible to the poller via
# ``actions/runs/{run_id}/jobs``. Two validators live in SEPARATE workflow
# files and were therefore structurally invisible to this gate before this
# entry existed — a red run of either could never turn "CI Summary" red:
#
#   - "DB ownership CI twin (B1)"        -> .github/workflows/check-db-ownership.yml
#   - "LLM refs drift check (OMN-11932)" -> .github/workflows/check-llm-refs-drift.yml
#     (removed by OMN-19391 together with the generated constants it checked:
#     with no generator and no generated file there is nothing left to drift)
#
# Both workflow files previously gated their `pull_request` trigger behind an
# `on.pull_request.paths:` filter, so before asserting them here their
# triggers were converted to always-fire + an in-job short-circuit (the
# omnibase_infra dispatch-parity-gate/deploy-gate pattern) — a job that is
# asserted must ALWAYS produce a check-run, never silently omit one because
# the touched paths didn't match.
#
# These are resolved against ``commits/{sha}/check-runs`` (NOT the in-run
# jobs endpoint — a different workflow file is a different Actions run) and
# are STRICT: present + completed + conclusion == 'success' only. Unlike
# GATE_JOBS, 'skipped' is NOT accepted here — after the always-fire
# conversion, a GitHub-level skip on one of these two check-runs would itself
# be anomalous un-enforcement (the in-job short-circuit means a
# no-relevant-changes PR still completes with a 'success' conclusion, never a
# workflow-level 'skipped').
EXPECTED_EXTERNAL_CONTEXTS: tuple[str, ...] = (
    "DB ownership CI twin (B1)",
    # OMN-18796 (epic OMN-18775): the no-new-advisory-job gate, called from
    # .github/workflows/advisory-job-gate.yml against the omniclaude reusable
    # pinned by commit. Registered HERE rather than in live branch protection
    # because this repository's own committed snapshot records that no agent
    # may mutate required_status_checks
    # (tests/unit/scripts/ci/fixtures/required_status_checks_snapshot.json,
    # `_meta.note`); L4 is a first-class enforcement surface under the required
    # "CI Summary" umbrella and carries the same merge-blocking force without a
    # live branch-protection write. The caller carries no `paths:` and no
    # `branches:` filter, so it reports on every pull-request shape and cannot
    # be legitimately absent -- the admission condition this tuple requires.
    "advisory-job-gate / advisory-job-gate",
)

# The L4 producers do not share an event contract. The CI Summary poller runs
# on more event shapes than any individual producer, so treating the union as
# required for every event turns a producer that cannot fire into a permanent
# pending verdict. These maps state the live producer contracts explicitly.
#
# `merge_group` and `schedule` deliberately have no external contexts: none of
# the two producer workflows fires on either event today. This is an explicit,
# tested applicability decision, not an absence that is read as a pass. An
# unknown event is rejected by `external_contexts_for_event`.
_DB_OWNERSHIP_EXTERNAL_CONTEXTS: tuple[str, ...] = EXPECTED_EXTERNAL_CONTEXTS[:1]
EXTERNAL_CONTEXTS_BY_EVENT: dict[str, tuple[str, ...]] = {
    "pull_request": EXPECTED_EXTERNAL_CONTEXTS,
    "push": _DB_OWNERSHIP_EXTERNAL_CONTEXTS,
    "merge_group": (),
    "workflow_dispatch": _DB_OWNERSHIP_EXTERNAL_CONTEXTS,
    "schedule": (),
}


def external_contexts_for_event(event_name: str) -> tuple[str, ...]:
    """Return the L4 contexts whose producer actually fires for ``event_name``.

    The caller passes GitHub's event name explicitly. Missing or unknown events
    fail closed rather than defaulting to an empty applicability set, which
    would turn a poller wiring regression into a green verdict.
    """

    try:
        return EXTERNAL_CONTEXTS_BY_EVENT[event_name]
    except KeyError as error:
        raise ValueError(
            f"unsupported CI event for L4 contexts: {event_name!r}"
        ) from error


# Spec-required validator covering jobs (OMN-14127 load-bearing property).
#
# These are the ci.yml jobs the operator-locked rollup-coverage spec
# (architecture-handshakes/validator-requirements.yaml →
# model_b_rollup_enforcement.repos.omnibase_core.validator_jobs) maps every
# spec-required validator onto, resolved from job KEY to job NAME. Each runs
# UNCONDITIONALLY in ci.yml (no `if:`, no `needs:` — verified 2026-07-07), so on
# any triggered event it always runs to a terminal success/failure and NEVER
# legitimately skips.
#
# Therefore the completeness anchor requires each of these PRESENT + completed +
# strictly SUCCESS. A SKIPPED (or absent) spec-required validator is a gate
# FAILURE, not a pass: a silent path-filter/skip that drops a required validator
# out of gating must NOT green the required context. This is a DIRECT,
# defense-in-depth check — it does not delegate to the aggregate Quality Gate's
# own strict `== success` aggregation to catch a dropped leaf.
#
# `tests/unit/scripts/ci/test_ci_summary_gate.py::test_spec_required_validator_jobs_match_spec`
# pins this tuple to the spec (validator_jobs covering job NAMES), so a NEW
# spec-required validator cannot silently escape this anchor: adding it to the
# spec forces adding its covering job here, or CI fails.
SPEC_REQUIRED_VALIDATOR_JOBS: tuple[str, ...] = (
    "Code Quality",  # lint (ruff-format-check, mypy-type-check)
    "Mypy Validation Scripts",  # mypy-validation-scripts (mypy-type-check, arch-002)
    "Core-Infra Boundary",  # core-infra-boundary (arch-002-no-transport-imports)
    "Enum Governance Check",  # enum-governance
    "Naming Conventions",  # naming-conventions
    "Pydantic Patterns",  # pydantic-patterns
    "AI Slop Patterns",  # aislop-patterns
    "Doc-Content Scan",  # doc-content-scan
    "Typed Bootstrap Environment Boundary (OMN-17744)",  # typed-bootstrap-environment-boundary
    "SPDX Headers",  # spdx-headers
    "Duplicate Registry Ids",  # duplicate-registry-ids (OMN-14401)
    "Hardcoded Topic Validator",  # hardcoded-topic-validator (OMN-14430)
    "Runtime Identity Validator",  # runtime-identity-validator (OMN-17308)
)

# Conclusions that count as "provably passed".
GOOD_CONCLUSIONS: frozenset[str] = frozenset({"success", "skipped"})

# OMN-18355 -- how long a `cancelled` L4 external context is treated as
# "awaiting its replacement" rather than as this head's answer.
#
# A cancellation is not a verdict. The producer was stopped before it could
# decide, and in the measured shape it was stopped BY the thing that is about
# to re-run it: a PR-body PATCH fires a second `pull_request` run of a workflow
# whose `types:` include `edited`, GitHub cancels the in-flight first run under
# the same concurrency group, and the replacement posts its own check-run
# seconds later. Reading that cancellation as a failure records a terminal
# verdict on a row that exists only because a newer run of the same producer
# took its place.
#
# 10 minutes is deliberately SHORTER than the window below: a cancellation's
# replacement is already running when the cancellation is written, whereas a
# companion-race red waits on a separate automation cycle.
CANCELLED_SUPERSESSION_GRACE_S: int = 600

# OMN-17864 -- how long a `failure` or `skipped` L4 external context is treated
# as "a verdict a re-run is about to replace" rather than as this head's answer.
#
# MECHANISM, measured on omnibase_infra#3779 and replayed in that repository's
# tests/fixtures/omn17864/: on a ticketed PR the change-control evidence
# companion is minted by AUTOMATION after the PR opens. Until it lands the PR
# body carries no evidence-source stamp and the Receipt Gate (`verify / verify`)
# is legitimately red. When the companion merges, automation PATCHes the PR
# body; every workflow whose `types:` include `edited` re-fires; the Receipt
# Gate re-runs and goes green ON ITS OWN. `CI Summary` polled inside that
# window, recorded FAILURE on a row that had completed 47 seconds earlier, and
# exited. The replacement row concluded `success` three minutes later. Only a
# human rerun cleared it, and that rerun passed with NO CHANGE TO THE PR --
# which is the proof that nothing was ever wrong with the head.
#
# THE WINDOW IS MEASURED, NOT CHOSEN. Over the 30 merged `dev` PRs sampled in
# omnibase_infra, 16 exhibited this shape; every one recovered, the slowest in
# 6.8 minutes, the median in 1.9. 20 minutes is ~3x the slowest observed and
# still well under this poller's own deadline.
#
# THIS RELAXES NOTHING THAT WAS EVER A STABLE VERDICT: a red older than the
# window still fails, an absent/unparseable/future `completed_at` still fails,
# `timed_out` and `action_required` are untouched, a missing clock restores the
# strict pre-grace reading, the poller's deadline still converts a sustained
# PENDING into FAILURE, and NOTHING here can resolve a context green -- only a
# real green check-run can.
EXTERNAL_FAILURE_SUPERSESSION_GRACE_S: int = 1200

#: Conclusions a re-run of the same producer can replace, and which therefore
#: get the OMN-17864 window. `failure` is the measured companion race.
#: `skipped` is the same race reached by a different route, measured on
#: omnibase_infra#3793: a producer whose job `needs:` a gate that failed for the
#: same unmerged companion is SKIPPED rather than run, so its row is a statement
#: about its DEPENDENCY, never about this head. Its rerun concluded `success` 38
#: seconds after `CI Summary` had already recorded FAILURE on the stale skip.
#:
#: THIS DOES NOT REOPEN THE SKIP-AS-PASS VECTOR (OMN-15057 / OMN-14854). That
#: vector is `skipped` read as SUCCESS. Here it is read as NO VERDICT YET: the
#: context is held pending, a real verdict may supersede it, and if none arrives
#: it still FAILS at the window. The L4 bar is unchanged -- only `success` ever
#: passes there.
#:
#: `cancelled` is absent deliberately: it has its own, shorter window
#: (:data:`CANCELLED_SUPERSESSION_GRACE_S`). `timed_out` and `action_required`
#: are absent because neither is produced by a producer that an automatic re-run
#: replaces.
SUPERSEDABLE_CONCLUSIONS: frozenset[str] = frozenset({"failure", "skipped"})

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_PENDING = 2


@dataclass(frozen=True)
class JobState:
    """The latest-attempt state of a single workflow job."""

    name: str
    status: str  # queued | in_progress | completed | waiting | ...
    conclusion: str | None  # success | failure | cancelled | skipped | timed_out | None
    run_attempt: int
    # ISO-8601; the instant this row concluded. Populated for L4 check-run rows
    # (the supersession windows are measured against it) and left ``None`` for
    # in-run job rows, which no window applies to.
    completed_at: str | None = None


def _job_states(
    jobs: list[dict[str, object]],
    *,
    run_attempt: int | None = None,
) -> list[JobState]:
    """Return authoritative job rows while preserving same-attempt duplicates.

    When ``run_attempt`` is provided, only rows from that workflow attempt are
    considered. This prevents stale failed/cancelled rows from an earlier
    attempt from becoming authoritative for a current rerun.

    Without ``run_attempt``, only the latest observed attempt for each job name
    is authoritative. Multiple rows for the same job name and same attempt are
    preserved so the default-deny sweep cannot hide a failed duplicate behind a
    later successful duplicate row.
    """

    states: list[JobState] = []
    for raw in jobs:
        name = str(raw.get("name") or "")
        if not name:
            continue
        raw_attempt = raw.get("run_attempt")
        try:
            attempt = int(raw_attempt) if isinstance(raw_attempt, (int, str)) else 1
        except (TypeError, ValueError):
            attempt = 1
        if run_attempt is not None and attempt != run_attempt:
            continue
        conclusion = raw.get("conclusion")
        states.append(
            JobState(
                name=name,
                status=str(raw.get("status") or ""),
                conclusion=None if conclusion is None else str(conclusion),
                run_attempt=attempt,
            )
        )

    if run_attempt is not None:
        return states

    latest_attempt_by_name: dict[str, int] = {}
    for state in states:
        latest_attempt_by_name[state.name] = max(
            latest_attempt_by_name.get(state.name, 0),
            state.run_attempt,
        )
    return [
        state
        for state in states
        if state.run_attempt == latest_attempt_by_name[state.name]
    ]


def dedup_latest(
    jobs: list[dict[str, object]],
    *,
    run_attempt: int | None = None,
) -> dict[str, JobState]:
    """Collapse authoritative job rows to one entry per job name.

    This is used for aggregate gate completeness reporting. The default-deny
    failure sweep intentionally uses :func:`_job_states` directly so duplicate
    same-attempt rows remain visible.
    """

    latest: dict[str, JobState] = {}
    for state in _job_states(jobs, run_attempt=run_attempt):
        latest[state.name] = state
    return latest


def _is_skipped_row(raw: dict[str, object]) -> bool:
    """True for a completed check-run whose conclusion is ``skipped``."""

    return (
        str(raw.get("status") or "") == "completed"
        and str(raw.get("conclusion") or "") == "skipped"
    )


def _skip_partition_key(raw: dict[str, object]) -> tuple[str, str]:
    """Partition key for skip supersession: ``(context name, head SHA)``.

    The head SHA is load-bearing, not decoration. A ``skipped`` row is only a
    re-trigger artifact when a non-skipped row exists for the same name ON THE
    SAME HEAD; a non-skipped row on a DIFFERENT head is a verdict about a
    different commit and must not clear it. Partitioning by name alone would
    let a ``success`` recorded on an earlier head silently suppress a
    ``skipped`` on the head actually being gated — the exact skip-as-pass
    vector (OMN-15057 / OMN-14854) the strict external bar exists for.

    Rows carrying no ``head_sha`` field all share the ``""`` partition, so a
    payload without head SHAs behaves exactly as it did before this guard.
    Unreachable through the sanctioned caller — it fetches
    ``commits/{sha}/check-runs`` for one head — but the safety of that rested
    on convention, and this makes it a property of the function.
    """

    return (str(raw.get("name") or ""), str(raw.get("head_sha") or ""))


def drop_superseded_skips(
    check_runs: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Drop ``skipped`` rows for a ``(name, head_sha)`` that also carries a
    non-skipped row (OMN-18062).

    MECHANISM this closes, measured on onex_change_control#8709 (2026-09-08): a
    ``gh pr edit`` of the PR body fires a SECOND ``pull_request`` run of a
    workflow whose ``types:`` include ``edited``. A job in that run whose own
    ``if:`` excludes ``edited`` is SKIPPED, and GitHub writes a FRESH check-run
    with conclusion ``skipped`` onto the same, unchanged head SHA where that
    very job reported ``success`` 64 seconds earlier. Latest-wins resolution in
    :func:`_external_check_states` picks the skip, L4 admits only ``success``
    (see :data:`EXPECTED_EXTERNAL_CONTEXTS`), and ``CI Summary`` fails closed on
    a head nothing regressed on. Re-running ``CI Summary`` cannot clear it — the
    skip is and stays the newest row for that name — so only a new head SHA can,
    and every lane that edits a PR body (OCC autobind stamps, union-resolves)
    pays a re-push cycle.

    A ``skipped`` row is evidence about a WORKFLOW RUN — a job's ``if:`` was
    false for that run's event — not about the head. When a non-skipped row for
    the same name exists on the same head, that row is the verdict about the
    head and the skip is a re-trigger artifact.

    What this deliberately does NOT relax:

    * ``skipped`` with **no** non-skipped row for that name still stands and
      still fails closed — a producer whose ``if:`` was false for the whole life
      of the head never ran, which is exactly the skip-as-pass vector
      (OMN-15057 / OMN-14854) the strict external bar exists for.
    * A ``failure`` (or ``cancelled``) after a ``success`` still wins on
      recency — a failure IS a verdict about the head.
    * A still-running row is non-skipped, so a later skip can never suppress
      PENDING into a stale green.
    * A skip on a DIFFERENT head SHA. Supersession is partitioned by
      ``(name, head_sha)``, not by name alone — see
      :func:`_skip_partition_key`.
    """

    non_skipped_keys = {
        _skip_partition_key(raw)
        for raw in check_runs
        if str(raw.get("name") or "") and not _is_skipped_row(raw)
    }
    return [
        raw
        for raw in check_runs
        if not (_is_skipped_row(raw) and _skip_partition_key(raw) in non_skipped_keys)
    ]


def _external_check_states(
    check_runs: list[dict[str, object]],
) -> dict[str, JobState]:
    """Collapse ``commits/{sha}/check-runs`` rows to one entry per check-run name.

    That endpoint has no ``run_attempt`` field like the Actions jobs endpoint —
    a rerun instead POSTs a new check-run row under the same name. Resolution
    is **latest wins** by ``(started_at, id)`` — deliberately the same rule
    GitHub itself applies when deciding a required status check from several
    same-named check-runs on one SHA — so a stale failed rerun can never
    outrank a fresh success, mirroring the run-attempt dedup used for in-run
    jobs above.

    OMN-16332 ADDED THE ``id`` COMPONENT. ``started_at`` alone is only
    second-granular, and this function previously resolved a tie by keeping
    whichever row came LAST IN THE PAYLOAD ARRAY. The check-runs endpoint makes
    no ordering guarantee, so a tie between two same-second rows was decided by
    a non-signal: a stale failure arriving last silently outranked the success
    beside it. The check-run ``id`` is monotonically increasing and orders those
    rows by actual creation, so nothing is left to array position. Rows with no
    ``id`` sort as ``0`` and therefore lose a tie to any row that has one,
    rather than winning it by position.

    A stricter "most-blocking across all same-named runs" rule was measured in
    omnibase_infra and REJECTED: because check-runs accumulate on a SHA forever,
    most-blocking makes any transient red permanent and removes re-run as a
    recovery path. Latest-wins is the measured choice, not the convenient one.

    Rows are read after :func:`drop_superseded_skips`, so a re-trigger skip
    cannot supersede a real conclusion already recorded for that name on this
    head (OMN-18062).
    """

    best: dict[str, JobState] = {}
    ordering: dict[str, tuple[str, int]] = {}
    for raw in drop_superseded_skips(check_runs):
        name = str(raw.get("name") or "")
        if not name:
            continue
        try:
            run_id = int(str(raw.get("id") or 0))
        except (TypeError, ValueError):
            run_id = 0
        key = (str(raw.get("started_at") or ""), run_id)
        if name in ordering and key <= ordering[name]:
            continue
        conclusion = raw.get("conclusion")
        completed_at = raw.get("completed_at")
        ordering[name] = key
        best[name] = JobState(
            name=name,
            status=str(raw.get("status") or ""),
            conclusion=None if conclusion is None else str(conclusion),
            run_attempt=1,
            completed_at=None if completed_at is None else str(completed_at),
        )
    return best


def _parse_timestamp(raw: str | None) -> datetime | None:
    """Parse a GitHub ISO-8601 ``Z`` timestamp, or ``None`` if unreadable."""

    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _within(state: JobState, now: datetime | None, grace_s: int) -> bool:
    """True when ``state`` concluded within ``grace_s`` either side of ``now``.

    The symmetric bound is not sloppiness. A ``completed_at`` slightly in the
    future is ordinary clock skew between GitHub and the runner and must stay
    provisional; a ``completed_at`` further in the future than the window is a
    clock so wrong the row cannot be reasoned about, and fails now rather than
    waiting forever on it.
    """

    if now is None:
        return False
    completed = _parse_timestamp(state.completed_at)
    if completed is None:
        return False
    return -grace_s <= (now - completed).total_seconds() <= grace_s


def cancellation_is_provisional(state: JobState, now: datetime | None) -> bool:
    """True while a ``cancelled`` L4 row is still awaiting its replacement.

    OMN-18355. See :data:`CANCELLED_SUPERSESSION_GRACE_S` for the mechanism.
    """

    if state.conclusion != "cancelled":
        return False
    return _within(state, now, CANCELLED_SUPERSESSION_GRACE_S)


def supersedable_verdict_is_provisional(state: JobState, now: datetime | None) -> bool:
    """True while a supersedable L4 row is inside its re-run window.

    OMN-17864. See :data:`SUPERSEDABLE_CONCLUSIONS` for which conclusions
    qualify and why, and :data:`EXTERNAL_FAILURE_SUPERSESSION_GRACE_S` for the
    measurement behind the window.
    """

    if state.conclusion not in SUPERSEDABLE_CONCLUSIONS:
        return False
    return _within(state, now, EXTERNAL_FAILURE_SUPERSESSION_GRACE_S)


def verdict_is_provisional(state: JobState, now: datetime | None) -> bool:
    """True when this row is a verdict an automatic replacement is due to replace.

    The union of the two windows, and the single place the poller's "keep
    waiting" decision is made, so the two cannot drift apart.

    FAIL-CLOSED IN EVERY UNCERTAIN CASE:

    * ``now is None`` (no clock supplied) -> not provisional -> fails now, so a
      caller that forgets the time enforces the OLD, stricter behaviour.
    * an absent or unparseable ``completed_at`` -> not provisional -> fails now.
    * a row older than its window -> not provisional -> fails now.
    * a ``completed_at`` further in the FUTURE than its window -> fails now.
    * a conclusion in neither graced set -> fails now.

    And the poller's own deadline still converts a sustained PENDING into
    FAILURE, so nothing here can make a required context green or absent.
    """

    return cancellation_is_provisional(state, now) or (
        supersedable_verdict_is_provisional(state, now)
    )


def provisional_external_verdicts(
    check_runs: list[dict[str, object]],
    *,
    expected: tuple[str, ...] = EXPECTED_EXTERNAL_CONTEXTS,
    now: datetime | None = None,
) -> list[str]:
    """The subset of ``expected`` held pending by a due automatic replacement.

    Reporting only. The poller's log is the diagnostic surface for a wedged PR,
    and "pending because a red is about to be re-run" must not read the same as
    "pending because nothing has started".
    """

    latest = _external_check_states(check_runs)
    return sorted(
        name
        for name in expected
        if (st := latest.get(name)) is not None
        and st.status == "completed"
        and st.conclusion != "success"
        and verdict_is_provisional(st, now)
    )


def evaluate_external(
    check_runs: list[dict[str, object]],
    *,
    expected: tuple[str, ...] = EXPECTED_EXTERNAL_CONTEXTS,
    now: datetime | None = None,
) -> tuple[list[str], list[str]]:
    """Return ``(failures, missing_or_pending)`` for L4 EXPECTED_EXTERNAL_CONTEXTS.

    STRICT success-only, mirroring :data:`STRICT_SUCCESS_JOBS`: each name in
    ``expected`` must be present with ``status == 'completed'`` and
    ``conclusion == 'success'``. Absent, still-running, skipped, failed, and
    cancelled are never a silent pass — absent/still-running is
    missing-or-pending (poll again, fail-closed at the caller's deadline);
    everything else present+completed+not-success is a failure.

    OMN-17864 / OMN-18355: a non-success row still inside its re-run window
    (:func:`verdict_is_provisional`) is missing-or-pending rather than a
    failure — a replacement is demonstrably due and the poller should look
    again. Nothing here can make such a row SUCCEED: it stays out of the
    success path, it is re-read on the next poll, and it fails as soon as its
    window closes. ``now`` is the observation time those windows are measured
    against; omitting it is the strict, pre-OMN-17864 reading.
    """

    latest = _external_check_states(check_runs)
    failures: list[str] = []
    missing_or_pending: list[str] = []
    for name in expected:
        st = latest.get(name)
        if st is None or st.status != "completed":
            missing_or_pending.append(name)
        elif st.conclusion == "success":
            continue
        elif verdict_is_provisional(st, now):
            missing_or_pending.append(name)
        else:
            failures.append(name)
    return sorted(failures), sorted(missing_or_pending)


def evaluate(
    jobs: list[dict[str, object]],
    *,
    run_attempt: int | None = None,
    self_name: str = SELF_JOB_NAME,
    gate_jobs: tuple[str, ...] = GATE_JOBS,
    allowlist: frozenset[str] = SOFT_ALLOWLIST,
    required_validator_jobs: tuple[str, ...] = SPEC_REQUIRED_VALIDATOR_JOBS,
    external_check_runs: list[dict[str, object]] | None = None,
    external_contexts: tuple[str, ...] = EXPECTED_EXTERNAL_CONTEXTS,
    now: datetime | None = None,
) -> tuple[int, str]:
    """Return ``(exit_code, human_report)`` for the current job snapshot.

    ``now`` is the observation time the OMN-17864 / OMN-18355 supersession
    windows are measured against. Omitting it is the strict, pre-OMN-17864
    reading: every non-success L4 row fails on the poll that observes it.
    """

    latest = dedup_latest(jobs, run_attempt=run_attempt)
    observed = _job_states(jobs, run_attempt=run_attempt)

    # (1) Default-deny failure sweep over every present+completed job.
    sweep_failures = sorted(
        {
            state.name
            for state in observed
            if state.name != self_name
            and state.name not in allowlist
            and state.status == "completed"
            and state.conclusion not in GOOD_CONCLUSIONS
        }
    )

    # (1b) Strict-success jobs (OMN-15222): unconditional ci.yml jobs whose
    #     SKIPPED/CANCELLED conclusion is anomalous un-enforcement and must fail
    #     closed. The GATE_JOBS completeness anchor accepts ``skipped``, so
    #     without this a skip would silently un-enforce the gate (mirrors
    #     omniclaude's OMN-14350 STRICT_SUCCESS_JOBS and the omnibase_infra
    #     STRICT_GATE_JOBS posture of the OMN-15214 canary).
    strict_success_failures = sorted(
        name
        for name in STRICT_SUCCESS_JOBS
        if (st := latest.get(name)) is not None
        and st.status == "completed"
        and st.conclusion != "success"
    )
    sweep_failures = sorted(set(sweep_failures) | set(strict_success_failures))

    # (2) Spec-required-validator anchor (OMN-14127 load-bearing): each covering
    #     job runs unconditionally in ci.yml, so it must be present + completed +
    #     strictly SUCCESS. A completed-but-not-success conclusion (SKIPPED /
    #     neutral / failure / cancelled) is a coverage FAILURE — a silently
    #     skipped spec-required validator must NOT green the gate. (failure /
    #     cancelled are also caught by the sweep; the net-new enforcement here is
    #     that SKIPPED does not pass for these jobs.)
    validator_not_success = sorted(
        job
        for job in required_validator_jobs
        if job in latest
        and latest[job].status == "completed"
        and latest[job].conclusion != "success"
    )
    validator_missing_or_pending = [
        job
        for job in required_validator_jobs
        if job not in latest or latest[job].status != "completed"
    ]

    # (3) Completeness anchor over the aggregate gates (present + completed).
    gate_missing_or_pending = [
        g
        for g in gate_jobs
        if (latest.get(g) is None or latest[g].status != "completed")
    ]

    # (4) L4 EXPECTED_EXTERNAL_CONTEXTS: validators living in a DIFFERENT
    #     workflow file, resolved against commits/{sha}/check-runs rather than
    #     this run's job list. See EXPECTED_EXTERNAL_CONTEXTS docstring above.
    external_failures, external_missing_or_pending = evaluate_external(
        external_check_runs or [], expected=external_contexts, now=now
    )
    external_provisional = provisional_external_verdicts(
        external_check_runs or [], expected=external_contexts, now=now
    )

    args = (
        latest,
        gate_jobs,
        required_validator_jobs,
        sweep_failures,
        validator_not_success,
        gate_missing_or_pending,
        validator_missing_or_pending,
        external_contexts,
        external_failures,
        external_missing_or_pending,
        external_provisional,
    )

    if sweep_failures or validator_not_success or external_failures:
        return EXIT_FAILURE, _report("FAILURE", *args)
    if (
        gate_missing_or_pending
        or validator_missing_or_pending
        or external_missing_or_pending
    ):
        return EXIT_PENDING, _report("PENDING", *args)
    return EXIT_SUCCESS, _report("SUCCESS", *args)


def _report(
    verdict: str,
    latest: dict[str, JobState],
    gate_jobs: tuple[str, ...],
    required_validator_jobs: tuple[str, ...],
    sweep_failures: list[str],
    validator_not_success: list[str],
    gate_missing_or_pending: list[str],
    validator_missing_or_pending: list[str],
    external_contexts: tuple[str, ...] = (),
    external_failures: list[str] | None = None,
    external_missing_or_pending: list[str] | None = None,
    external_provisional: list[str] | None = None,
) -> str:
    external_failures = external_failures or []
    external_missing_or_pending = external_missing_or_pending or []
    external_provisional = external_provisional or []
    lines = [f"CI Summary verdict: {verdict}", f"  jobs observed: {len(latest)}"]
    lines.append("  aggregate gates:")
    for g in gate_jobs:
        st = latest.get(g)
        lines.append(
            f"    - {g}: <absent>"
            if st is None
            else f"    - {g}: {st.status}/{st.conclusion}"
        )
    lines.append("  spec-required validators (must be completed + success):")
    for v in required_validator_jobs:
        st = latest.get(v)
        lines.append(
            f"    - {v}: <absent>"
            if st is None
            else f"    - {v}: {st.status}/{st.conclusion}"
        )
    if external_contexts:
        lines.append(
            "  L4 external contexts (other workflow files, must be completed + success):"
        )
        for name in external_contexts:
            if name in external_failures:
                lines.append(f"    - {name}: <present, not success>")
            elif name in external_missing_or_pending:
                lines.append(f"    - {name}: <absent or pending>")
            else:
                lines.append(f"    - {name}: success")
    if sweep_failures:
        lines.append(f"  default-deny sweep failures: {', '.join(sweep_failures)}")
    if validator_not_success:
        lines.append(
            "  spec-required validators not success (skip/fail is a coverage gap): "
            + ", ".join(validator_not_success)
        )
    if gate_missing_or_pending:
        lines.append(f"  gates missing/pending: {', '.join(gate_missing_or_pending)}")
    if validator_missing_or_pending:
        lines.append(
            "  spec-required validators missing/pending: "
            + ", ".join(validator_missing_or_pending)
        )
    if external_failures:
        lines.append(
            "  L4 external contexts not success (coverage gap): "
            + ", ".join(external_failures)
        )
    if external_missing_or_pending:
        lines.append(
            "  L4 external contexts missing/pending: "
            + ", ".join(external_missing_or_pending)
        )
    if external_provisional:
        # Distinct from the line above on purpose: "pending because a red is
        # about to be replaced by an automatic re-run" and "pending because
        # nothing has started" are different diagnoses of a wedged PR, and one
        # line reads the same for both.
        lines.append(
            "  L4 external contexts awaiting an automatic replacement "
            "(cancelled, or failed or skipped inside the re-run window): "
            + ", ".join(external_provisional)
        )
    return "\n".join(lines)


def _load_jobs(path: str | None) -> list[dict[str, object]]:
    if path is None or path == "-":
        raw = sys.stdin.read()
    else:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    data = json.loads(raw)
    # Accept either the raw endpoint object ({"jobs": [...]}) or a bare array.
    if isinstance(data, dict):
        jobs = data.get("jobs", [])
    else:
        jobs = data
    if not isinstance(jobs, list):
        raise ValueError("jobs payload must be a list or an object with a 'jobs' array")
    return jobs


def _load_check_runs(path: str | None) -> list[dict[str, object]]:
    """Load L4 external check-run rows (``commits/{sha}/check-runs`` shape)."""
    if path is None:
        return []
    with open(path, encoding="utf-8") as handle:
        raw = handle.read()
    if not raw.strip():
        return []
    data = json.loads(raw)
    # Accept either the raw endpoint object ({"check_runs": [...]}) or a bare array.
    if isinstance(data, dict):
        check_runs = data.get("check_runs", [])
    else:
        check_runs = data
    if not isinstance(check_runs, list):
        raise ValueError(
            "check-runs payload must be a list or an object with a 'check_runs' array"
        )
    return check_runs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--jobs-file",
        default="-",
        help="Path to the GitHub Actions jobs JSON (default: stdin). Accepts the "
        "raw endpoint object or a bare array of job objects.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Print the verdict report and exit 0 regardless (diagnostics only).",
    )
    parser.add_argument(
        "--run-attempt",
        type=int,
        default=None,
        help="Evaluate only rows for this GitHub Actions run_attempt.",
    )
    parser.add_argument(
        "--external-check-runs-file",
        default=None,
        help="Path to the commits/{sha}/check-runs JSON for L4 "
        "EXPECTED_EXTERNAL_CONTEXTS (default: none supplied -> treated as "
        "all-missing, i.e. PENDING until supplied).",
    )
    parser.add_argument(
        "--event-name",
        required=True,
        help="GitHub event name selecting the L4 external-context contract.",
    )
    args = parser.parse_args(argv)

    jobs = _load_jobs(args.jobs_file)
    external_check_runs = _load_check_runs(args.external_check_runs_file)
    try:
        external_contexts = external_contexts_for_event(args.event_name)
    except ValueError as error:
        parser.error(str(error))
        return EXIT_FAILURE
    code, report = evaluate(
        jobs,
        run_attempt=args.run_attempt,
        external_check_runs=external_check_runs,
        external_contexts=external_contexts,
        # The observation time the OMN-17864 / OMN-18355 windows are measured
        # against. It is the process's own wall clock and has NO CLI surface --
        # deliberately, because a caller-assertable time would let a long-dead
        # red be held provisional indefinitely, which is the one way these
        # windows could become a bypass.
        #
        # OMITTING IT SILENTLY DISABLES BOTH. `verdict_is_provisional` returns
        # False on `now is None` by design -- fail-closed, so a forgetful
        # caller enforces the old strict reading rather than waiting. That is
        # the right default and a terrible silent outcome: the first port of
        # this change into a sibling repository changed the gate module and not
        # its poller, and the gate shipped completely inert with every unit
        # test green.
        now=datetime.now(UTC),
    )
    selected = ", ".join(external_contexts) or "<none: no producer for this event>"
    print(f"L4 event/context contract: {args.event_name}: {selected}")  # noqa: T201
    print(report)  # noqa: T201 — CLI verdict report to stdout for the poll loop
    if args.report_only:
        return EXIT_SUCCESS
    return code


if __name__ == "__main__":
    raise SystemExit(main())
