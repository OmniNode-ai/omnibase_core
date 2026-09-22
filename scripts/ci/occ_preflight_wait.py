# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Bounded wait for ``occ-preflight / eligibility`` (OMN-17864).

Why this module exists
-----------------------
``occ-preflight.yml``'s "Resolve Evidence-Source" step used to be a single
bash check: if the PR body had no ``Evidence-Source:`` line yet, or the cited
onex_change_control companion PR had not merged yet, the step ``exit 1``'d in
2-8 seconds. Both conditions are TRANSIENT — the OCC autobind PATCHes the
stamp onto the body after the PR opens, and the companion merges some minutes
later — but the aggregator that reads this job's conclusion never re-runs, so
a real, would-eventually-pass PR was recorded FAILURE forever.

Measured over 188 merged product PRs in the 48h to 2026-09-16T14:47Z: 53 PRs
had their first CI run conclude BEFORE the cited companion merged, and 0 of
those 53 concluded success. Of the 135 whose first run concluded after the
companion merged, 77 (57%) succeeded. Time from CI-run start to companion
merge: median 16 min, p75 26, p90 41, p95 55, max 239 -- a 1500-second budget
covers 141/188 (75%).

The fix is the producer, not the aggregator: this job already sits inside a
CI run whose sibling job, "OCC Companion Merged Gate (OMN-15214)"
(``scripts/ci/check_occ_companion_merged.py``), polls the IDENTICAL fact
(live PR body, cited companion merged or not) for up to
``DEADLINE_SECONDS=1500`` at ``POLL_INTERVAL_SECONDS=30``, unconditionally,
on every run. Giving ``occ-preflight`` the same bounded wait costs no
additional wall clock on the critical path -- the run already pays for that
budget elsewhere. 1500/30 is that already-declared, already-paid budget for
the same fact in the same run, not a new number invented for this module.

Shape
-----
Mirrors ``occ_preflight_heal.py``: a pure ``decide_preflight_wait`` verdict
function, a :class:`GhPort` protocol for the live reads it needs, a
:class:`GhCli` implementation backed by the ``gh`` binary, and a thin
``main()`` polling driver. The pure function is exhaustively unit-tested;
the client is exercised only by the workflow itself.

Every branch fails closed. An unreadable PR body is ``FAIL_NOW``, not
``WAIT`` -- there is nothing to re-read that will fix itself. A companion
CLOSED without merging is ``FAIL_NOW`` -- that is the exact OMN-15214
incident state, and waiting cannot un-close it. A malformed evidence-source
value is ``FAIL_NOW`` -- waiting cannot repair an authoring error. A
evidence-source SHA that is not an ancestor of any onex_change_control
durable branch is ``FAIL_NOW`` -- onex_change_control is squash-only, so a
feature-branch head SHA can never become one (OMN-15216), and no amount of
elapsed time changes that. Only ``stamp_absent`` and ``companion_unmerged``
are genuinely retryable, and even those convert to ``DEADLINE`` (also a hard
failure) once ``elapsed_seconds >= deadline_seconds``.

The one exemption (OMN-18848)
-----------------------------
``stamp_absent`` is retryable only while a stamp can still arrive. For a
post-release version bump -- a manifest-and-lockfile diff with no behavioural
claim -- no changed file CAN be RED-derivable, so the OCC autobind producer
DECLINES to mint and no stamp is ever coming. This gate polled the full 1500s
and failed closed with ``stamp_absent`` anyway, because it never read the
producer's outcome at all (live: omnimarket#2685, job 105923152940), which
made every PR the release Dependency Cascade opens unmergeable.

When the producer's terminal outcome for THIS head SHA is ``DECLINED`` with a
reason beginning ``skip:DEPENDENCY_PIN_ONLY``, and only then, the missing
stamp resolves to :attr:`EnumPreflightWaitOutcome.NOT_REQUIRED` instead. This
is emphatically NOT a skip token: nothing in the PR body is read for it. The
producer classifies the DIFF itself and records the verdict on an
``occ-autobind / outcome`` check-run bound to the PR's current head SHA, so an
author cannot assert it and a new commit invalidates it (the new SHA carries
no outcome, and the gate is back on its ordinary wait-then-fail path). The
token set is a cross-repo contract with omnimarket's producer and its
Companion Merged Gate -- see
``omnimarket/scripts/ci/check_occ_companion_merged.py``'s
``AUTOBIND_NO_COMPANION_REQUIRED_REASONS``.

The read of that check-run fails OPEN and only open: an unreadable check-run
list yields ``None``, which leaves every existing branch exactly as it was.
Evidence written by another repo's runtime must never be able to fail this
gate on its own.

The third consumer (OMN-18882)
------------------------------
``.github/workflows/receipt-gate.yml`` is a third gate in the same family and
hard-fails the identical PR on its own missing-``Evidence-Source`` check
(measured on omnimarket#2701 at 10:38:18Z). It is a bash gate with no Python
process of its own, so it drives this module's
``--check-no-companion-required`` probe over
:func:`wait_for_no_companion_required`. That probe reuses this module's token
set, predicate and check-run reader unchanged -- the token is defined once, in
one place, for every gate in the family. Its ONLY difference is direction of
failure: it fails CLOSED, because its caller's existing behaviour is a hard
failure rather than a poll, so an unreadable outcome must leave that hard
failure standing rather than waive it.

That probe is BOUNDED-WAITING, not one-shot (OMN-19164)
-------------------------------------------------------
OMN-18882 landed it as a single read, on the premise that "by the time that
gate runs, this run has already paid the OMN-15214 budget for the same fact".
That premise is false and was measured false: the Receipt Gate job and the
autobind producer are triggered by the SAME event and run CONCURRENTLY, and
the gate is the faster of the two. On ``omnimarket#2775`` head
``96fd645574c5ab9271913021fc53af770a361166`` the gate read at 07:44:06Z, hard
failed, and the producer posted its ``skip:DEPENDENCY_PIN_ONLY`` decline at
07:44:12Z -- six seconds too late. On ``#2776`` the same two events landed in
the other order and the identical PR class passed. Across 24 sampled bump PRs
in two repos every failure was this race and the near-miss margin was 1-4
seconds, so which way a post-release bump resolved was decided by runner
scheduling.

The fix is ORDERING, NOT PERMISSION, and the distinction is the whole design:

* "no outcome recorded YET" and "no outcome will EVER be recorded" were one
  state, and resolving a not-yet-known premise as a refusal is what made a
  correct exemption unreachable. They are now two states -- see
  :class:`EnumNoCompanionProbeVerdict` -- and only the first one waits.
* Nothing about WHAT qualifies moved. The head-SHA binding, the ``DECLINED``
  requirement and the pin-only token set are untouched, so an outcome posted
  against an earlier commit is still invisible and an author still cannot
  assert anything.
* A verdict that IS in hand is terminal on the first read. A MINTED outcome,
  or a decline for any other reason, means a companion is genuinely owed; no
  later poll changes that, and waiting on it would buy nothing but delay.
* The deadline fails CLOSED, under
  :attr:`EnumNoCompanionProbeVerdict.INDETERMINATE`'s own detail text naming
  the elapsed budget -- distinct from the absent-outcome text, so a lost race
  and a genuine no-outcome case are told apart on the PR (AC3).

A ``merge_group`` (or any non-``pull_request``) event always ``PROCEED``s
immediately, never waits. Invariant I2 in ``occ-preflight.yml``'s own header
requires a ``merge_group`` run to re-validate fully against the pinned
evidence and fail fast; a bounded wait on that event would blur "fast" and
would let a stale in-flight PR-open evaluation leak into the merge-queue
gate, which is the one thing I2 exists to prevent.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess  # fixed argv, no shell, trusted gh binary
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Protocol
from urllib.parse import quote

EXIT_OK: Final[int] = 0
EXIT_ERROR: Final[int] = 1

OCC_REPO_DEFAULT: Final[str] = "OmniNode-ai/onex_change_control"

# Branches on which an evidence-source commit SHA counts as durable evidence.
# Mirrors check_occ_companion_merged.OCC_DURABLE_BRANCHES.
OCC_DURABLE_BRANCHES: Final[tuple[str, ...]] = ("dev", "main")

# The already-paid OMN-15214 budget for the identical fact in the same run.
# See module docstring -- this is not a new number, it is the existing one.
DEFAULT_DEADLINE_SECONDS: Final[int] = 1500
DEFAULT_POLL_INTERVAL_SECONDS: Final[int] = 30

# OMN-19164 -- the Receipt Gate probe's own budget, deliberately NOT the 1500s
# one above. That budget belongs to a gate whose job is to wait for a human or
# a mint; this one waits only for a producer that is already running in the
# same event, and every second of it is spent on a PR that will hard fail if
# the wait expires. The numbers are sized from measurement, not taste: the
# producer posted its outcome 25s after PR open while the gate read at 19s
# (omnimarket#2775), and the widest observed producer latency on a first run
# was ~97s (omnibase_infra#3942). 180s is a little under twice that, and 5s
# resolves a 1-4s race without busy-polling the check-runs API.
DEFAULT_NO_COMPANION_DEADLINE_SECONDS: Final[int] = 180
DEFAULT_NO_COMPANION_POLL_INTERVAL_SECONDS: Final[int] = 5

EVIDENCE_SOURCE_RE: Final[re.Pattern[str]] = re.compile(
    r"^Evidence-Source:\s+(\S.*)$", re.IGNORECASE | re.MULTILINE
)
OCC_PR_REF_RE: Final[re.Pattern[str]] = re.compile(r"^OCC#(\d+)$", re.IGNORECASE)
HEX_SHA_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{7,40}$")

_ENFORCED_EVENT: Final[str] = "pull_request"

# OMN-18069 -- the autobind producer's terminal outcome, posted as a check-run
# on the product PR's own head SHA. The name and the marker prefix are a
# cross-repo contract; changing either is a two-repo change. Mirrors
# check_occ_companion_merged.AUTOBIND_OUTCOME_{CHECK_NAME,MARKER_PREFIX}.
AUTOBIND_OUTCOME_CHECK_NAME: Final[str] = "occ-autobind / outcome"
AUTOBIND_OUTCOME_MARKER_PREFIX: Final[str] = "occ-autobind-outcome:"
AUTOBIND_OUTCOME_DECLINED: Final[str] = "DECLINED"

# OMN-18848 -- the one DECLINED reason that means "this PR owes no companion",
# as opposed to "this PR owes evidence nobody has written yet". See the module
# docstring. Mirrors check_occ_companion_merged.
# AUTOBIND_NO_COMPANION_REQUIRED_REASONS byte-for-byte; the two must move
# together or the fleet's definition of the exemption splits in silence.
AUTOBIND_NO_COMPANION_REQUIRED_REASONS: Final[tuple[str, ...]] = (
    "skip:DEPENDENCY_PIN_ONLY",
)

# OMN-18647 -- the DECLINED reasons on which the producer has TERMINALLY stood
# down for this head SHA: it will not mint, now or on any later poll, and the
# only path forward is a hand-authored companion on the OMN-15247 path.
#
# An ALLOWLIST, deliberately, and the direction of the asymmetry is the whole
# point. Reading an in-flight mint as terminal tells a lane to hand-author a
# companion into a live race: that is OMN-18881, where OCC#10524 collided with
# an in-flight mint, raised SupersessionCheckBindingError 166 times and evicted
# the node_occ_companion_effect consumer for four and a half hours. A reason
# this set does not name keeps waiting, which costs runner minutes and nothing
# else. `skip:LEASE_HELD` in particular is a SECOND PRODUCER MINTING RIGHT NOW
# and must never appear here.
AUTOBIND_TERMINAL_DECLINE_REASONS: Final[tuple[str, ...]] = (
    "skip:NO_RED_DERIVABLE_CHECK",
    "skip:DEFER_HAND_AUTHORED",
)


class EnumAutobindReadStatus(StrEnum):
    """Why :meth:`GhPort.read_autobind_outcome` has, or has not, an outcome.

    OMN-18647. The three are not interchangeable and collapsing them is the
    defect this enum exists to remove: ABSENT means the producer has not
    reported yet (wait), UNREADABLE means we could not ask (wait, but say so
    -- never infer a verdict from a failed read), and READ means the producer
    reported and the verdict is in hand.
    """

    READ = "read"
    ABSENT = "absent"
    UNREADABLE = "unreadable"


@dataclass(frozen=True)
class ModelAutobindOutcomeRead:
    """One read of the head-SHA-bound ``occ-autobind / outcome`` check-run."""

    status: EnumAutobindReadStatus
    outcome: str = ""
    reason: str = ""


class EnumNoCompanionProbeVerdict(StrEnum):
    """One read's verdict in the Receipt Gate's pin-only probe (OMN-19164).

    The three-way split IS the fix. OMN-18882 had two outcomes, exempt and
    not-exempt, which forced "the producer has not reported yet" to be
    reported as "the producer says you owe evidence" -- a not-yet-known
    premise resolved as a refusal, which is how a correct exemption became
    unreachable on the PR class it was written for.

    ``INDETERMINATE`` is the only verdict that waits, and waiting is all it
    does: it is not a pass, it never becomes one on the deadline, and the
    caller that runs out of budget holding it fails exactly as it did before
    this ticket. ``NOT_EXEMPT`` is a verdict the producer actually reached,
    so it is terminal on the first read -- re-polling a MINTED outcome or a
    non-pin decline delays a PR that genuinely owes evidence.
    """

    EXEMPT = "exempt"
    NOT_EXEMPT = "not_exempt"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class ModelNoCompanionProbeRead:
    """One classification of one :class:`ModelAutobindOutcomeRead`.

    A frozen dataclass rather than a Pydantic model to match every other
    verdict type in this module: it is a CI entrypoint that must import under
    a bare ``python3`` on a runner with no project environment, so it takes no
    third-party import. ``detail`` is the sentence the job log prints, and it
    is part of the contract -- AC3 turns on the timeout text differing from
    the absent-outcome text.
    """

    verdict: EnumNoCompanionProbeVerdict
    detail: str

    @property
    def is_terminal(self) -> bool:
        return self.verdict is not EnumNoCompanionProbeVerdict.INDETERMINATE


class EnumPreflightWaitOutcome(StrEnum):
    """One value per terminal or poll-again branch of :func:`decide_preflight_wait`."""

    PROCEED = "proceed"
    # OMN-18848: the producer classified this head's diff as dependency-pin-only,
    # so no OCC companion exists or will. Terminal, and a PASS -- distinct from
    # PROCEED because there is no OCC SHA to pin and nothing downstream to check
    # out against.
    NOT_REQUIRED = "not_required"
    WAIT = "wait"
    FAIL_NOW = "fail_now"
    DEADLINE = "deadline"
    # OMN-18647: the producer declined TERMINALLY for this head SHA. A
    # failure, like FAIL_NOW, but a distinct token because the remedy is
    # distinct: nothing is broken, and a hand-authored companion is the
    # designed path rather than a workaround.
    DECLINED_TERMINAL = "declined_terminal"


@dataclass(frozen=True)
class ModelPreflightWaitDecision:
    """One poll's verdict. ``reason`` is a stable machine-readable token;
    ``detail`` names the PR, the companion, and the elapsed seconds for a
    human reading the job log."""

    outcome: EnumPreflightWaitOutcome
    reason: str
    detail: str

    @property
    def should_continue_polling(self) -> bool:
        return self.outcome is EnumPreflightWaitOutcome.WAIT

    @property
    def is_terminal_failure(self) -> bool:
        return self.outcome in (
            EnumPreflightWaitOutcome.FAIL_NOW,
            EnumPreflightWaitOutcome.DEADLINE,
            EnumPreflightWaitOutcome.DECLINED_TERMINAL,
        )


def parse_evidence_source(pr_body: str) -> str | None:
    """First ``Evidence-Source:`` value in *pr_body*, or ``None``."""
    match = EVIDENCE_SOURCE_RE.search(pr_body)
    return match.group(1).strip() if match else None


def is_no_companion_required(reason: str) -> bool:
    """Whether a DECLINED ``reason=`` names a verdict that needs no companion.

    OMN-18848. Matched on the reason TOKEN the producer writes at the start of
    the field, never on the prose after it, so rewording a message cannot
    silently change a verdict -- and, more sharply, so a message that
    *describes* the classifier refusing ("classifier refused
    skip:DEPENDENCY_PIN_ONLY because a source file changed") cannot read as the
    classifier accepting. This predicate returning ``True`` is the only path on
    which a PR with no evidence stamp is allowed past this gate.
    """
    return any(
        reason.strip().startswith(marker)
        for marker in AUTOBIND_NO_COMPANION_REQUIRED_REASONS
    )


def is_terminal_decline(reason: str) -> bool:
    """Whether a DECLINED ``reason=`` names a verdict that will never mint.

    OMN-18647. Matched on the reason TOKEN at the START of the field, exactly
    as :func:`is_no_companion_required` is and for the same reason: a message
    that DESCRIBES a token ("considered skip:NO_RED_DERIVABLE_CHECK and
    rejected that classification") must not read as the producer declaring it.

    Returning ``True`` shortens a 1500 s wait to seconds. Returning ``False``
    costs runner time and nothing else, so every uncertain input returns
    ``False`` -- including the live mislabel, a ``no-op: ... already bound to
    OCC#N`` reason the producer writes as DECLINED on a path that in fact
    succeeded.
    """
    stripped = reason.strip()
    return any(
        stripped.startswith(marker) for marker in AUTOBIND_TERMINAL_DECLINE_REASONS
    )


def read_autobind_outcome_from_check_runs(
    check_runs: Sequence[object],
) -> tuple[str, str] | None:
    """``(outcome, reason)`` from the newest completed autobind outcome run.

    OMN-18069/OMN-18848. The producer writes a machine-readable first line into
    the check-run summary::

        occ-autobind-outcome: DECLINED repo=... pr=... correlation_id=... reason=...

    ``None`` when no such completed check-run is present, or when its summary
    carries no marker line -- the ordinary case for a PR whose autobind has not
    reported yet.
    """
    # Typed Sequence[object] rather than a list of dicts because the live
    # caller hands this straight-from-JSON data: the per-element isinstance
    # guard below is a real runtime check, not a redundant one.
    latest: dict[str, object] | None = None
    for run in check_runs:
        if not isinstance(run, dict):
            continue
        if str(run.get("name") or "") != AUTOBIND_OUTCOME_CHECK_NAME:
            continue
        if str(run.get("status") or "") != "completed":
            continue
        if latest is None or str(run.get("completed_at") or "") >= str(
            latest.get("completed_at") or ""
        ):
            latest = run
    if latest is None:
        return None

    output = latest.get("output")
    summary = str(output.get("summary") or "") if isinstance(output, dict) else ""
    for line in summary.splitlines():
        stripped = line.strip()
        if not stripped.startswith(AUTOBIND_OUTCOME_MARKER_PREFIX):
            continue
        payload = stripped[len(AUTOBIND_OUTCOME_MARKER_PREFIX) :].strip()
        if not payload:
            break
        outcome = payload.split(None, 1)[0]
        marker = "reason="
        reason = payload.split(marker, 1)[1].strip() if marker in payload else ""
        return outcome, reason
    return None


def classify_no_companion_required(
    read: ModelAutobindOutcomeRead,
) -> ModelNoCompanionProbeRead:
    """Pure verdict for ONE read of the head-SHA-bound autobind outcome.

    OMN-19164 split this out of the live probe so every branch is decided by a
    function with no clock, no network and no sleep, exhaustively unit-tested
    -- the same pure-function/polling-driver split
    :func:`decide_preflight_wait` already uses, and the reason a verdict here
    is falsifiable by a unit test rather than by a live lane.

    Which reads WAIT and which are terminal is the substance:

    ``ABSENT``
        The producer has not reported against this head yet. It is running in
        the same event as the caller and is routinely the slower of the two,
        so this is the race and the only ordinary reason to poll.
    ``UNREADABLE``
        We could not ask -- transport error, rate limit, malformed response.
        Also INDETERMINATE, because a failed read is not a verdict and must
        never be read as one; a transient 502 that resolves on the next poll
        is the same shape as the race and deserves the same budget. It fails
        closed on the deadline exactly as before.
    ``READ`` and not ``DECLINED``
        The producer MINTED, so a companion exists and is owed. Terminal.
    ``READ``, ``DECLINED``, non-pin reason
        A verdict the producer reached: this PR still owes a citation. No
        later poll changes it. Terminal.
    ``READ``, ``DECLINED``, pin-only reason
        The exemption, unchanged from OMN-18882 in every particular.
    """
    if read.status is EnumAutobindReadStatus.UNREADABLE:
        # OMN-18647 split this out of the absent case below. Both are
        # indeterminate and neither is a verdict, but a gate that cannot say
        # which one it hit sends its reader looking for the wrong thing.
        return ModelNoCompanionProbeRead(
            verdict=EnumNoCompanionProbeVerdict.INDETERMINATE,
            detail=(
                "the occ-autobind outcome check-run for this PR's current head "
                "SHA could not be READ (transport error, rate limit or malformed "
                "response); that is not the same as the producer having declined "
                "and is never read as one"
            ),
        )
    if read.status is EnumAutobindReadStatus.ABSENT:
        return ModelNoCompanionProbeRead(
            verdict=EnumNoCompanionProbeVerdict.INDETERMINATE,
            detail=(
                "no completed occ-autobind outcome is recorded against this PR's "
                "current head SHA yet (an outcome posted against an earlier "
                "commit is deliberately invisible here)"
            ),
        )
    outcome_word, outcome_reason = read.outcome, read.reason
    if outcome_word.strip().upper() != AUTOBIND_OUTCOME_DECLINED:
        return ModelNoCompanionProbeRead(
            verdict=EnumNoCompanionProbeVerdict.NOT_EXEMPT,
            detail=(
                f"the occ-autobind outcome for this head is "
                f"'{outcome_word.strip()}', not {AUTOBIND_OUTCOME_DECLINED}; only "
                "a decline can mean no companion is owed"
            ),
        )
    if not is_no_companion_required(outcome_reason):
        return ModelNoCompanionProbeRead(
            verdict=EnumNoCompanionProbeVerdict.NOT_EXEMPT,
            detail=(
                f"the occ-autobind outcome for this head is DECLINED with reason "
                f"'{outcome_reason.strip()}', which is not the dependency-pin-only "
                "verdict; this PR still owes an evidence citation"
            ),
        )
    return ModelNoCompanionProbeRead(
        verdict=EnumNoCompanionProbeVerdict.EXEMPT,
        detail=(
            "the occ-autobind producer classified this head's diff as "
            f"dependency-pin-only (reason '{outcome_reason.strip()}'), so no OCC "
            "evidence companion exists or will be minted for it. The verdict is "
            "DERIVED from the diff by the producer, never asserted in the PR "
            "body, and it is bound to this head SHA -- a new commit carries no "
            "outcome and re-opens this gate (OMN-18848)"
        ),
    )


def wait_for_no_companion_required(
    *,
    repo: str,
    pr_number: str,
    client: GhPort,
    deadline_seconds: int = DEFAULT_NO_COMPANION_DEADLINE_SECONDS,
    poll_interval_seconds: int = DEFAULT_NO_COMPANION_POLL_INTERVAL_SECONDS,
    sleep: Callable[[float], object] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    emit: Callable[[str], object] = print,
) -> tuple[bool, str]:
    """Whether the producer affirmatively declined a companion for this head.

    OMN-18882. The bounded wait above is one consumer of the exemption; the
    Receipt Gate (``.github/workflows/receipt-gate.yml``) is another, and it is
    a bash gate with no Python process of its own, so it needs a decisive
    process-level answer rather than an importable predicate. This function --
    and the ``--check-no-companion-required`` CLI mode over it -- is that
    answer, resolved through the SAME
    :data:`AUTOBIND_NO_COMPANION_REQUIRED_REASONS`,
    :func:`is_no_companion_required` and
    :func:`read_autobind_outcome_from_check_runs` the wait uses. The token is
    defined once, here, for every gate in the family; a gate re-spelling it in
    its own bash is how the fleet's definition of the exemption splits in
    silence.

    Polls :func:`classify_no_companion_required` until it reaches a terminal
    verdict or *deadline_seconds* elapses, whichever comes first. The client's
    read re-resolves the PR's head on EVERY poll, so a commit landing mid-wait
    is read against its own new SHA rather than the one this call started on
    -- the head-SHA binding holds across the wait, it is not a snapshot taken
    at entry.

    Unlike the module's main wait, this one fails CLOSED, because the caller's
    existing behaviour is a hard failure rather than a poll: an unresolvable
    head, an unreadable check-run list, an absent outcome, an outcome on a
    different SHA, every non-pin reason and an expired budget all return
    ``False``, which leaves the Receipt Gate's ``Evidence-Source`` hard fail
    exactly where it was. ``True`` is returned only for an affirmative
    DECLINED whose reason token is the pin-only one, recorded against the PR's
    CURRENT head SHA.

    *sleep* and *monotonic* are injected so the tests drive the deadline
    deterministically instead of spending real seconds; the defaults are the
    real clock and nothing in the live path passes anything else.

    Every poll it spends is ANNOUNCED through *emit*. A gate that silently
    waits is indistinguishable in a job log from the one-shot read this
    replaces, so the one thing a reader needs to know -- that the probe is
    waiting for the producer rather than having already refused -- would be
    invisible exactly when someone is debugging a slow or missing outcome.
    """
    start = monotonic()
    last = classify_no_companion_required(
        client.read_autobind_outcome(repo=repo, pr_number=pr_number)
    )
    while True:
        if last.verdict is EnumNoCompanionProbeVerdict.EXEMPT:
            return True, last.detail
        if last.verdict is EnumNoCompanionProbeVerdict.NOT_EXEMPT:
            return False, f"{last.detail}, so no exemption applies"

        elapsed = int(monotonic() - start)
        if elapsed >= deadline_seconds:
            # AC3: the deadline's own sentence, distinct from the
            # absent-outcome one it quotes, so a LOST RACE and a producer that
            # never reports are distinguishable in the job log. Both fail; a
            # reader who cannot tell them apart chases the wrong remedy.
            return False, (
                f"{last.detail}; waited {elapsed}s of a {deadline_seconds}s "
                "budget for the producer to report and it did not, so no "
                "exemption applies (OMN-19164 timeout, NOT a verdict that a "
                "companion is owed -- if the producer is simply slow, re-run "
                "this job once its outcome check-run is present)"
            )
        emit(
            f"occ-autobind no-companion-required: waiting "
            f"({elapsed}s/{deadline_seconds}s) -- {last.detail}"
        )
        sleep(poll_interval_seconds)
        last = classify_no_companion_required(
            client.read_autobind_outcome(repo=repo, pr_number=pr_number)
        )


def _wait_or_deadline(
    *, reason: str, detail: str, elapsed_seconds: int, deadline_seconds: int
) -> ModelPreflightWaitDecision:
    """Shared tail of every retryable branch (rule 8 of the design)."""
    if elapsed_seconds >= deadline_seconds:
        return ModelPreflightWaitDecision(
            outcome=EnumPreflightWaitOutcome.DEADLINE,
            reason=reason,
            detail=(
                f"{detail} -- poll deadline ({deadline_seconds}s) reached after "
                f"{elapsed_seconds}s; failing closed"
            ),
        )
    return ModelPreflightWaitDecision(
        outcome=EnumPreflightWaitOutcome.WAIT,
        reason=reason,
        detail=f"{detail} ({elapsed_seconds}s elapsed of {deadline_seconds}s budget)",
    )


def decide_preflight_wait(
    *,
    pr_body: str | None,
    companion_state: str | None,
    cited_sha_is_ancestor: bool,
    elapsed_seconds: int,
    deadline_seconds: int,
    event_name: str,
    autobind_outcome: tuple[str, str] | None = None,
    autobind_read_failed: bool = False,
    terminal_decline_fast_exit: bool = False,
) -> ModelPreflightWaitDecision:
    """Pure verdict for one poll iteration.

    ``companion_state`` is the live onex_change_control companion PR state
    when the evidence-source stamp cites one (``"MERGED"`` / ``"OPEN"`` /
    ``"CLOSED"``), or ``None`` when the stamp cites a SHA instead, or when a
    companion was cited but its state could not be read (a retryable
    transport failure, distinct from an authoritative CLOSED).

    ``cited_sha_is_ancestor`` is only consulted when the stamp is SHA-shaped;
    it is ignored otherwise.

    ``autobind_outcome`` is the OCC autobind producer's ``(outcome, reason)``
    for the PR's CURRENT head SHA, or ``None`` when no outcome was recorded or
    the check-run list could not be read. It is consulted in the
    ``stamp is None`` branch and nowhere else (OMN-18848): a PR that DOES cite
    evidence is evaluated on that evidence whatever the producer said.

    ``autobind_read_failed`` says the producer's surface could not be READ
    (rate limit, 5xx, malformed JSON), as against not having reported yet.
    OMN-18647: the two produce the same wait and different text, and neither
    is ever a decline -- a verdict is never inferred from a failed read.

    ``terminal_decline_fast_exit`` gates every OMN-18647 behaviour. Left at
    its default, this function returns today's verdict and today's text for
    every input, which is what keeps the canary caller the ONLY caller whose
    behaviour moves until the follow-up removes the flag fleet-wide.
    """
    if event_name != _ENFORCED_EVENT:
        return ModelPreflightWaitDecision(
            outcome=EnumPreflightWaitOutcome.PROCEED,
            reason="non_pull_request_event",
            detail=(
                f"event '{event_name}' is not '{_ENFORCED_EVENT}'; invariant I2 "
                "requires a merge_group run to re-validate against pinned evidence "
                "and fail fast, so the bounded wait never applies here"
            ),
        )

    if pr_body is None:
        return ModelPreflightWaitDecision(
            outcome=EnumPreflightWaitOutcome.FAIL_NOW,
            reason="body_unreadable",
            detail=(
                "the PR body could not be read; failing closed rather than waiting "
                "on a surface that cannot be observed"
            ),
        )

    stamp = parse_evidence_source(pr_body)
    if stamp is None:
        # OMN-18848: the one shape in which a missing stamp is not a pending
        # one. Nothing here is asserted by the PR -- the producer classified
        # this head's DIFF and recorded the verdict on a head-SHA-bound
        # check-run. Fail-open on the read: `autobind_outcome is None` falls
        # straight through to the unchanged wait path below.
        if autobind_outcome is not None:
            outcome_word, outcome_reason = autobind_outcome
            if outcome_word.strip().upper() == AUTOBIND_OUTCOME_DECLINED and (
                is_no_companion_required(outcome_reason)
            ):
                return ModelPreflightWaitDecision(
                    outcome=EnumPreflightWaitOutcome.NOT_REQUIRED,
                    reason="no_companion_required",
                    detail=(
                        "the occ-autobind producer classified this head's diff as "
                        "dependency-pin-only (reason "
                        f"'{outcome_reason.strip()}'), so no OCC evidence "
                        "companion exists or will be minted for it. The verdict "
                        "is DERIVED from the diff by the producer, never asserted "
                        "in the PR body, and it is bound to this head SHA -- a "
                        "new commit carries no outcome and re-opens this gate "
                        "(OMN-18848)"
                    ),
                )

            # OMN-18647. The producer has stood down for this head SHA. No
            # later poll changes that, so the 1500s budget buys nothing and
            # the author reads a timeout instead of the reason.
            if terminal_decline_fast_exit and (
                outcome_word.strip().upper() == AUTOBIND_OUTCOME_DECLINED
                and is_terminal_decline(outcome_reason)
            ):
                return ModelPreflightWaitDecision(
                    outcome=EnumPreflightWaitOutcome.DECLINED_TERMINAL,
                    reason="autobind_declined_terminal",
                    detail=(
                        "the occ-autobind producer TERMINALLY declined to mint a "
                        f"companion for this head SHA: {outcome_reason.strip()}. "
                        "No later poll changes this verdict, so this gate stops "
                        "now rather than spending its remaining budget. A "
                        "hand-authored OCC companion on the OMN-15247 path is "
                        "the designed remedy and is SAFE to author now -- the "
                        "producer has stood down for this head SHA, so there is "
                        "no in-flight mint to collide with (contrast OMN-18881). "
                        "It must be signed by a different lane than the one that "
                        "authored the ticket, and a new commit re-opens this "
                        "gate with a fresh verdict (OMN-18647)"
                    ),
                )

        if terminal_decline_fast_exit and autobind_read_failed:
            # Distinct from "the producer has not reported yet". Same wait,
            # same fail-closed deadline, honest text: an unreadable surface is
            # never evidence of a verdict in either direction.
            return _wait_or_deadline(
                reason="autobind_outcome_unreadable",
                detail=(
                    "the occ-autobind outcome check-run for this head SHA could "
                    "not be READ (transport error, rate limit or malformed "
                    "response) -- this is not the same as the producer not "
                    "having reported, and it is never read as a decline. Waiting "
                    "and failing closed; do NOT hand-author a companion on this "
                    "signal, because an unreadable surface cannot rule out an "
                    "in-flight mint (OMN-18881)"
                ),
                elapsed_seconds=elapsed_seconds,
                deadline_seconds=deadline_seconds,
            )

        in_flight_warning = (
            " -- hand-authoring a companion now is UNSAFE while a mint may be "
            "in flight: it collides with the producer's own mint and can evict "
            "the companion consumer (OMN-18881). Wait for a terminal outcome"
            if terminal_decline_fast_exit
            else ""
        )
        return _wait_or_deadline(
            reason="stamp_absent",
            detail=(
                "PR body has no evidence-source stamp line yet (the occ-autobind "
                f"mint may still be in flight){in_flight_warning}"
            ),
            elapsed_seconds=elapsed_seconds,
            deadline_seconds=deadline_seconds,
        )

    occ_ref = OCC_PR_REF_RE.match(stamp)
    is_hex_sha = HEX_SHA_RE.match(stamp.lower()) is not None

    if occ_ref is None and not is_hex_sha:
        return ModelPreflightWaitDecision(
            outcome=EnumPreflightWaitOutcome.FAIL_NOW,
            reason="stamp_malformed",
            detail=(
                f"evidence-source value '{stamp}' is neither 'OCC#<number>' nor a "
                "hex commit SHA; waiting cannot repair an authoring error"
            ),
        )

    if occ_ref is not None:
        companion_pr = occ_ref.group(1)
        state = (companion_state or "").upper()

        if state == "MERGED":
            return ModelPreflightWaitDecision(
                outcome=EnumPreflightWaitOutcome.PROCEED,
                reason="evidence_durable",
                detail=f"companion OCC#{companion_pr} is MERGED -- evidence is durable",
            )

        if state == "CLOSED":
            # The exact OMN-15214 incident state: an OPEN companion closed
            # without merging. Never poll; the evidence no longer exists.
            return ModelPreflightWaitDecision(
                outcome=EnumPreflightWaitOutcome.FAIL_NOW,
                reason="companion_closed_unmerged",
                detail=(
                    f"companion OCC#{companion_pr} is CLOSED without merging -- the "
                    "cited evidence no longer exists, and waiting cannot bring it back"
                ),
            )

        # "OPEN" or unresolved (a transient read failure on the companion
        # lookup itself) both retry: only an authoritative CLOSED is terminal.
        retry_reason = (
            "companion_unmerged" if state == "OPEN" else "companion_state_unresolved"
        )
        retry_detail = (
            f"companion OCC#{companion_pr} is still OPEN -- it must merge before "
            "this PR may merge"
            if state == "OPEN"
            else f"could not resolve the live state of companion OCC#{companion_pr} (retryable)"
        )
        return _wait_or_deadline(
            reason=retry_reason,
            detail=retry_detail,
            elapsed_seconds=elapsed_seconds,
            deadline_seconds=deadline_seconds,
        )

    # SHA-shaped stamp.
    if cited_sha_is_ancestor:
        return ModelPreflightWaitDecision(
            outcome=EnumPreflightWaitOutcome.PROCEED,
            reason="evidence_durable",
            detail=(
                f"evidence-source SHA {stamp} is an ancestor of an OCC durable "
                "branch -- evidence is durable"
            ),
        )
    return ModelPreflightWaitDecision(
        outcome=EnumPreflightWaitOutcome.FAIL_NOW,
        reason="sha_not_ancestor",
        detail=(
            f"evidence-source SHA {stamp} is not an ancestor of any OCC durable "
            f"branch {OCC_DURABLE_BRANCHES} -- onex_change_control is squash-only, "
            "so a feature-branch head SHA can never become one (OMN-15216); "
            "waiting cannot repair this"
        ),
    )


class GhPort(Protocol):
    """The live GitHub reads this poll needs."""

    def read_pr_body(self, *, repo: str, pr_number: str) -> str | None: ...

    def read_companion(
        self, *, occ_repo: str, pr_number: str
    ) -> tuple[str | None, str]: ...

    def canonicalize_sha(self, *, occ_repo: str, sha: str) -> str | None: ...

    def sha_is_ancestor(
        self, *, occ_repo: str, sha: str, branches: tuple[str, ...]
    ) -> bool: ...

    def read_autobind_outcome(
        self, *, repo: str, pr_number: str
    ) -> ModelAutobindOutcomeRead: ...


class GhCli:
    """:class:`GhPort` backed by the ``gh`` binary."""

    def _run(self, argv: list[str]) -> str | None:
        try:
            proc = subprocess.run(  # fixed argv, no shell
                argv, capture_output=True, text=True, timeout=60, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"::warning::gh invocation failed: {exc}", file=sys.stderr)
            return None
        if proc.returncode != 0:
            print(
                f"::warning::{' '.join(argv[:4])}... exited {proc.returncode}: "
                f"{proc.stderr.strip()[:300]}",
                file=sys.stderr,
            )
            return None
        return proc.stdout

    def read_pr_body(self, *, repo: str, pr_number: str) -> str | None:
        """The LIVE body via the REST API -- never the triggering event
        payload. occ-autobind PATCHes Evidence-Source onto the body AFTER the
        triggering event fired, which is exactly the race this module closes.
        """
        raw = self._run(
            ["gh", "api", f"repos/{repo}/pulls/{pr_number}", "--jq", ".body"]
        )
        if raw is None:
            return None
        text = raw.rstrip("\n")
        return "" if text == "null" else text

    def read_companion(
        self, *, occ_repo: str, pr_number: str
    ) -> tuple[str | None, str]:
        raw = self._run(
            [
                "gh",
                "pr",
                "view",
                pr_number,
                "--repo",
                occ_repo,
                "--json",
                "state,headRefOid,mergeCommit",
            ]
        )
        if raw is None:
            return None, ""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None, ""
        if not isinstance(data, dict):
            return None, ""
        state_raw = data.get("state")
        state = (
            str(state_raw).upper() if isinstance(state_raw, str) and state_raw else None
        )
        sha = ""
        if state == "MERGED":
            merge_commit = data.get("mergeCommit")
            if isinstance(merge_commit, dict):
                sha = str(merge_commit.get("oid") or "")
        else:
            head_ref_oid = data.get("headRefOid")
            sha = str(head_ref_oid) if isinstance(head_ref_oid, str) else ""
        return state, sha

    def canonicalize_sha(self, *, occ_repo: str, sha: str) -> str | None:
        raw = self._run(
            ["gh", "api", f"repos/{occ_repo}/commits/{sha}", "--jq", ".sha"]
        )
        text = raw.strip() if raw is not None else ""
        return text or None

    def read_autobind_outcome(
        self, *, repo: str, pr_number: str
    ) -> ModelAutobindOutcomeRead:
        """The producer's outcome for the PR's CURRENT head SHA.

        Head-SHA-bound by construction (OMN-18848): the head is re-read live on
        every poll and the check-runs are fetched for that SHA alone, so an
        outcome recorded against an earlier commit is invisible here.

        Fail-SAFE, in the sense that matters: a failed head read and a failed
        or unparseable check-run read report UNREADABLE, an absent outcome
        reports ABSENT, and both leave :func:`decide_preflight_wait` waiting.
        OMN-18647 separates the two only so the job log can say which
        happened -- no verdict is ever inferred from a read that failed,
        because the evidence is written by a different repo's runtime and an
        outage there must not become a verdict here.

        Selected SERVER-SIDE by check name rather than by scanning a page of
        results (OMN-18647). omnibase_infra#3874 carried 233 check-runs on
        2026-09-20 with its ``occ-autobind / outcome`` on page 2, so the
        previous single ``per_page=100`` page reported ABSENT for a PR whose
        outcome existed -- an arm that fires on the outcome is worth nothing
        on exactly the busy PRs that need it.
        """
        raw = self._run(
            [
                "gh",
                "pr",
                "view",
                pr_number,
                "--repo",
                repo,
                "--json",
                "headRefOid",
                "--jq",
                ".headRefOid",
            ]
        )
        head_sha = raw.strip() if raw is not None else ""
        if not head_sha or head_sha == "null":
            return ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.UNREADABLE)

        raw_runs = self._run(
            [
                "gh",
                "api",
                f"repos/{repo}/commits/{head_sha}/check-runs"
                f"?check_name={quote(AUTOBIND_OUTCOME_CHECK_NAME, safe='')}"
                "&per_page=100",
                "--jq",
                ".check_runs",
            ]
        )
        if raw_runs is None:
            return ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.UNREADABLE)
        try:
            data = json.loads(raw_runs)
        except json.JSONDecodeError:
            return ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.UNREADABLE)
        if not isinstance(data, list):
            return ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.UNREADABLE)
        parsed = read_autobind_outcome_from_check_runs(data)
        if parsed is None:
            return ModelAutobindOutcomeRead(status=EnumAutobindReadStatus.ABSENT)
        outcome, reason = parsed
        return ModelAutobindOutcomeRead(
            status=EnumAutobindReadStatus.READ, outcome=outcome, reason=reason
        )

    def sha_is_ancestor(
        self, *, occ_repo: str, sha: str, branches: tuple[str, ...]
    ) -> bool:
        for branch in branches:
            raw = self._run(
                [
                    "gh",
                    "api",
                    f"repos/{occ_repo}/compare/{branch}...{sha}",
                    "--jq",
                    ".status",
                ]
            )
            if raw is not None and raw.strip() in ("identical", "behind"):
                return True
        return False


_AUTOBIND_NOT_CONSULTED: Final[ModelAutobindOutcomeRead] = ModelAutobindOutcomeRead(
    status=EnumAutobindReadStatus.ABSENT
)


def _resolve_facts(
    client: GhPort, *, repo: str, pr_number: str, occ_repo: str
) -> tuple[str | None, str | None, bool, str, ModelAutobindOutcomeRead]:
    """One round of live reads. Returns (pr_body, companion_state,
    cited_sha_is_ancestor, resolved_sha, autobind)."""
    pr_body = client.read_pr_body(repo=repo, pr_number=pr_number)
    if pr_body is None:
        return None, None, False, "", _AUTOBIND_NOT_CONSULTED

    stamp = parse_evidence_source(pr_body)
    if stamp is None:
        # Read the producer outcome ONLY on the branch that can consult it
        # (OMN-18848), so a PR that already carries a stamp pays no extra API
        # calls and cannot have its verdict touched by this read.
        return (
            pr_body,
            None,
            False,
            "",
            client.read_autobind_outcome(repo=repo, pr_number=pr_number),
        )

    occ_ref = OCC_PR_REF_RE.match(stamp)
    if occ_ref is not None:
        state, sha = client.read_companion(
            occ_repo=occ_repo, pr_number=occ_ref.group(1)
        )
        return pr_body, state, False, sha, _AUTOBIND_NOT_CONSULTED

    if HEX_SHA_RE.match(stamp.lower()) is not None:
        canonical = client.canonicalize_sha(occ_repo=occ_repo, sha=stamp)
        resolved_sha = canonical or stamp
        is_ancestor = client.sha_is_ancestor(
            occ_repo=occ_repo, sha=resolved_sha, branches=OCC_DURABLE_BRANCHES
        )
        return pr_body, None, is_ancestor, resolved_sha, _AUTOBIND_NOT_CONSULTED

    # Malformed; decide_preflight_wait reports this itself from pr_body.
    return pr_body, None, False, "", _AUTOBIND_NOT_CONSULTED


def _write_github_output(name: str, value: str, *, github_output_path: str) -> None:
    # No os.environ read here by design (OMN-17744 typed-bootstrap-only
    # boundary): the caller resolves $GITHUB_OUTPUT in the workflow's bash
    # step and passes it explicitly via --github-output-path.
    if not github_output_path:
        return
    with open(github_output_path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def _build_parser() -> argparse.ArgumentParser:
    # Every value this CLI needs is passed explicitly by the caller (see
    # occ-preflight.yml's "Resolve Evidence-Source" step) -- no os.environ
    # fallback defaults, per the OMN-17744 typed-bootstrap-only boundary.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="")
    parser.add_argument("--pr-number", default="")
    parser.add_argument("--event-name", default="pull_request")
    parser.add_argument("--occ-repo", default=OCC_REPO_DEFAULT)
    parser.add_argument(
        "--deadline-seconds", type=int, default=DEFAULT_DEADLINE_SECONDS
    )
    parser.add_argument(
        "--poll-interval-seconds", type=int, default=DEFAULT_POLL_INTERVAL_SECONDS
    )
    parser.add_argument(
        "--github-output-path",
        default="",
        help="Value of $GITHUB_OUTPUT, resolved by the caller and passed explicitly.",
    )
    parser.add_argument(
        "--check-no-companion-required",
        action="store_true",
        help=(
            "OMN-18882 probe, for gates that are not this wait: exit 0 iff the "
            "occ-autobind producer recorded a dependency-pin-only DECLINE "
            "against the PR's CURRENT head SHA, else exit 1. Never reads the "
            "PR body, and fails closed on every indeterminate outcome. "
            "OMN-19164: bounded-waits for the producer to report rather than "
            "reading once, because the gate driving it and the producer run "
            "concurrently off the same event."
        ),
    )
    # OMN-19164. Knobs on the WAIT, never on the verdict: neither can admit a
    # PR the probe would otherwise refuse, because a shorter budget can only
    # reach the same fail-closed timeout sooner and a longer one can only
    # spend more seconds before the identical refusal. Deliberately NOT a
    # skip, allowlist or override input (AC5); the parser declares no such
    # option and a test reads these option strings to keep it that way.
    parser.add_argument(
        "--no-companion-deadline-seconds",
        type=int,
        default=DEFAULT_NO_COMPANION_DEADLINE_SECONDS,
        help=(
            "Budget for --check-no-companion-required to wait for the "
            "producer's head-SHA-bound outcome before failing closed."
        ),
    )
    parser.add_argument(
        "--no-companion-poll-interval-seconds",
        type=int,
        default=DEFAULT_NO_COMPANION_POLL_INTERVAL_SECONDS,
        help="Seconds between --check-no-companion-required polls.",
    )
    # OMN-18647. Off unless the caller asks for it, so the one pinned canary
    # caller is the only caller whose behaviour moves. NOT a bypass and NOT a
    # kill switch: it can only ever shorten a wait that was going to fail, and
    # every fail-closed branch is identical in both positions. The follow-up
    # that takes the fleet over deletes this flag and its workflow input.
    parser.add_argument(
        "--terminal-decline-fast-exit",
        action="store_true",
        help=(
            "End the wait immediately when the occ-autobind producer has "
            "TERMINALLY declined to mint for this head SHA, instead of "
            "polling to the deadline and reporting stamp_absent."
        ),
    )
    return parser


def main(argv: list[str] | None = None, *, gh: GhPort | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.repo or not args.pr_number:
        print("--repo and --pr-number are required", file=sys.stderr)
        return EXIT_ERROR

    client: GhPort = gh if gh is not None else GhCli()

    if args.check_no_companion_required:
        # OMN-18882: the probe the Receipt Gate drives. OMN-19164 made it a
        # bounded wait: the premise this once carried -- that the outcome is
        # already recorded by the time this gate runs -- was measured FALSE on
        # omnimarket#2775, where the producer posted six seconds after the
        # gate had already hard failed. It still fails closed on the deadline.
        exempt, detail = wait_for_no_companion_required(
            repo=args.repo,
            pr_number=args.pr_number,
            client=client,
            deadline_seconds=args.no_companion_deadline_seconds,
            poll_interval_seconds=args.no_companion_poll_interval_seconds,
        )
        print(f"occ-autobind no-companion-required: {str(exempt).lower()} -- {detail}")
        if not exempt:
            return EXIT_ERROR
        _write_github_output(
            "evidence_not_required", "true", github_output_path=args.github_output_path
        )
        return EXIT_OK

    start = time.monotonic()

    while True:
        elapsed = int(time.monotonic() - start)
        (
            pr_body,
            companion_state,
            cited_sha_is_ancestor,
            resolved_sha,
            autobind,
        ) = _resolve_facts(
            client, repo=args.repo, pr_number=args.pr_number, occ_repo=args.occ_repo
        )
        decision = decide_preflight_wait(
            pr_body=pr_body,
            companion_state=companion_state,
            cited_sha_is_ancestor=cited_sha_is_ancestor,
            elapsed_seconds=elapsed,
            deadline_seconds=args.deadline_seconds,
            event_name=args.event_name,
            autobind_outcome=(
                (autobind.outcome, autobind.reason)
                if autobind.status is EnumAutobindReadStatus.READ
                else None
            ),
            autobind_read_failed=(autobind.status is EnumAutobindReadStatus.UNREADABLE),
            terminal_decline_fast_exit=args.terminal_decline_fast_exit,
        )
        print(
            f"occ-preflight wait: [{decision.outcome.value}] {decision.reason} -- {decision.detail}"
        )

        if decision.outcome is EnumPreflightWaitOutcome.NOT_REQUIRED:
            # No `sha` output by design: there is no OCC companion to pin, and
            # emitting one would hand the downstream checkout a ref it must not
            # have. The downstream eligibility steps read this flag and skip.
            _write_github_output(
                "evidence_not_required",
                "true",
                github_output_path=args.github_output_path,
            )
            print(f"::notice::{decision.detail}")
            return EXIT_OK

        if decision.outcome is EnumPreflightWaitOutcome.PROCEED:
            if resolved_sha:
                _write_github_output(
                    "sha", resolved_sha, github_output_path=args.github_output_path
                )
                print(f"::notice::Evidence-Source resolved to OCC SHA: {resolved_sha}")
            return EXIT_OK

        if decision.is_terminal_failure:
            print(f"::error::{decision.detail}", file=sys.stderr)
            return EXIT_ERROR

        time.sleep(args.poll_interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
