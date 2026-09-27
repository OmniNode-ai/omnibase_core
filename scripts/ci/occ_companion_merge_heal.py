# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Re-run a preflight that gave up before its companion merged (OMN-18812).

Why this module exists
----------------------
``occ-preflight / eligibility`` waits a bounded ``1500`` seconds for the cited
onex_change_control companion to merge and then fails closed
(``omnibase_core`` ``scripts/ci/occ_preflight_wait.py``, OMN-17864). That
budget was sized on a measured distribution, and the distribution moved.

Re-measured 2026-09-19 over the 1000 most recently merged evidence companions
(``search/issues``, ``repo:OmniNode-ai/onex_change_control is:pr is:merged
created:>=2026-09-12 in:title evidence``), open-to-merge: p50 27.6 min, p75
50.8 min, p90 125.7 min, p95 183.7 min. The live budget covers 46.3% of them.
The OMN-17864 docstring's own basis, measured three days earlier, was p50 16
min / p95 55 min and "covers 141/188 (75%)"; p95 moved 3.3x in three days.

There is no number that fixes this. The job declares ``timeout-minutes: 30``,
so every admissible budget sits below p75, and a constant re-cut by hand
cannot track a distribution that moves faster than the re-cut.

The failure is also replicated rather than singular. 56 omniclaude workflows
each instantiate the preflight reusable as their own ``occ-preflight`` job and
gate a real check on ``needs: occ-preflight``. On ``omniclaude#2265``, head
``d75e0606``, that produced 42 ``occ-preflight / eligibility`` check runs on
one sha, 8 failure and 34 success, 29,107 seconds of summed wall clock, and 24
workflow runs that a human then re-ran by hand. Every failure started at
11:07:30Z or 11:08:06Z; the first-wave successes started at 11:07:30Z or
11:08:21Z. A 36-second difference in when the fleet picked the job up decided
the verdict on an identical fact.

What this does instead
----------------------
Nothing here changes the budget, and nothing here changes WHAT is required.
This module answers one question per open PR — *has the companion this PR is
blocked on merged since the preflight gave up?* — and, when the answer is yes,
re-runs the failed jobs of that PR's failed runs in place.

``gh run rerun --failed`` preserves the run id, so ``CI Summary`` re-polls the
same job list it always polls and observes the new verdict, and every job that
already passed keeps its result. The re-run executes the eligibility validator
from scratch against the merged companion SHA and can still fail. What is
removed is the human who types the command: all three of the 2026-09-19
occurrences were cleared that way and by nothing else.

Why a schedule, and not the companion's merge event
---------------------------------------------------
The event that makes the fact true is the companion merging, which happens in
``onex_change_control``. Dispatching from there into a product repo needs
``actions: write`` on the product repo, and no identity this org holds has it:
read live and recorded in OMN-18797, installation 148180820
(``onexbot-occ-writer``) holds ``actions: read``, installation 123040063
(``onexbot``) holds ``actions: read``, and the org PAT's uses inside that
workflow are ratcheted by OMN-16373. The remaining invocation point that needs
no new credential is a schedule inside the product repo, where the ambient
``GITHUB_TOKEN`` already carries ``actions: write``.

The in-repo events were each considered and each fires at the wrong moment.
``pull_request: edited`` fires when the autobind stamp lands, about a minute
after the push. ``workflow_run: completed`` on a preflight caller fires when
the wait deadlines. Both precede the median companion merge by tens of
minutes, which is exactly why ``omnibase_infra``'s OMN-18352 heal — which
listens to precisely those two — does not clear this failure.

Shape
-----
Mirrors ``omnibase_infra`` ``scripts/ci/occ_preflight_heal.py``: a pure
``decide_companion_heal`` verdict function, a :class:`GhPort` protocol for the
live reads and the one write, a :class:`GhCli` implementation backed by the
``gh`` binary, and a thin ``main()`` driver. The pure function is exhaustively
unit-tested; the client is exercised by the workflow itself.

Every branch that does not re-run says which branch it was. The defect that
produced ``omnibase_infra``'s heal was a green job that had healed nothing
behind a single "nothing to do" message covering both "there was nothing to
heal" and "I could not tell"; each refusal here carries its own
:class:`EnumCompanionHealOutcome`, and a PR whose state cannot be read at all
is reported and exits non-zero rather than passing as a clean no-op.

Cost and bounds
---------------
A re-run is issued only when the companion is already MERGED, so the re-run
this module spends is one the wait will satisfy on its first poll rather than
a second 1500-second budget against a fact that is still false. That is the
whole reason the companion state is read before the re-run and not after.

``MAX_HEAL_RUN_ATTEMPT`` is a hard backstop against an unforeseen loop: a run
already at the ceiling is refused whatever its state. The merged-companion
precondition is expected to do the actual work, because a healed run's
preflight passes and stops appearing in the failed set at all.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess  # fixed argv, no shell, trusted gh binary
import sys
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final, Protocol

EXIT_OK: Final[int] = 0
EXIT_ERROR: Final[int] = 1

OCC_REPO_DEFAULT: Final[str] = "OmniNode-ai/onex_change_control"

#: Backstop against an unforeseen re-trigger loop. A healed run's preflight
#: passes and leaves the failed set, so this ceiling is expected never to bind;
#: it exists so that an unforeseen state cannot produce an unbounded re-run.
MAX_HEAL_RUN_ATTEMPT: Final[int] = 5

#: Job-name markers for the preflight family, matched as case-insensitive
#: SUBSTRINGS rather than as a prefix.
#:
#: The first revision of this module matched ``name.startswith("occ-preflight")``
#: case-sensitively, and that missed two live shapes (found on `omnimarket#2676`
#: and `omniclaude#2263`, OMN-15727 AC1):
#:
#: * ``call-reject-skip-token / occ-preflight / eligibility`` -- a nested caller
#:   prefixes the reusable's job id with its own, so the name does not START
#:   with the marker even though it is the same job;
#: * ``OCC Preflight Dependency`` -- the poller that WAITS on eligibility, whose
#:   name differs in case and uses a space rather than a hyphen. On
#:   `omnimarket#2676` two runs had that job as their ONLY failure, so a
#:   prefix match skipped the exact runs the heal exists to re-run.
#:
#: Both markers are required: `occ preflight` alone would not match the hyphenated
#: reusable job, and `occ-preflight` alone would not match the dependency poller.
#: Deliberately NOT a bare `preflight`, which would sweep in unrelated jobs.
PREFLIGHT_JOB_MARKERS: Final[tuple[str, ...]] = ("occ-preflight", "occ preflight")


def is_preflight_job_name(name: str, *, markers: tuple[str, ...]) -> bool:
    """Whether a check-run or job name belongs to the preflight family.

    Case-insensitive substring, so a nested caller's prefix and the dependency
    poller's spelling both match. Under-matching here is not neutral: it skips
    the runs the heal exists to re-run, which is how the shipped prefix match
    missed both of `omnimarket#2676`'s red runs.
    """
    lowered = name.lower()
    return any(marker in lowered for marker in markers)


#: Mirrors ``occ_preflight_wait.EVIDENCE_SOURCE_RE`` and ``OCC_PR_REF_RE``. The
#: stamp is authored by the OCC autobind, so the two must agree on its shape.
EVIDENCE_SOURCE_RE: Final[re.Pattern[str]] = re.compile(
    r"^Evidence-Source:\s+(\S.*)$", re.IGNORECASE | re.MULTILINE
)
OCC_PR_REF_RE: Final[re.Pattern[str]] = re.compile(r"^OCC#(\d+)$", re.IGNORECASE)

#: The autobind producer's terminal-outcome check-run (OMN-18069). Mirrors
#: ``check_occ_companion_merged.AUTOBIND_OUTCOME_CHECK_NAME`` /
#: ``AUTOBIND_OUTCOME_MARKER_PREFIX`` / ``AUTOBIND_OUTCOME_DECLINED`` in this
#: same repo -- name and marker prefix are a cross-repo contract owned by
#: ``omnimarket`` ``occ_autobind_outcome.py``, not something this module may
#: redefine independently.
AUTOBIND_OUTCOME_CHECK_NAME: Final[str] = "occ-autobind / outcome"
AUTOBIND_OUTCOME_MARKER_PREFIX: Final[str] = "occ-autobind-outcome:"
AUTOBIND_OUTCOME_DECLINED: Final[str] = "DECLINED"

_PAGE_SIZE: Final[int] = 100

#: Ceiling on the open-PR listing. ``gh pr list`` truncates at ``--limit``
#: without saying so, so reaching this is an error rather than a result.
_OPEN_PR_LIMIT: Final[int] = 2000


class EnumCompanionHealOutcome(StrEnum):
    """Why the heal did or did not issue a re-run. One value per branch."""

    RERUN_REQUIRED = "rerun_required"
    NO_FAILED_PREFLIGHT = "no_failed_preflight"
    DRAFT_NOT_MINTED = "draft_not_minted"
    AUTOBIND_DECLINED = "autobind_declined"
    NO_EVIDENCE_STAMP = "no_evidence_stamp"
    NOT_COMPANION_FORM = "not_companion_form"
    COMPANION_UNMERGED = "companion_unmerged"
    COMPANION_CLOSED = "companion_closed"
    COMPANION_UNRESOLVED = "companion_unresolved"
    ATTEMPT_CEILING = "attempt_ceiling"
    NO_FAILED_RUNS = "no_failed_runs"


class EnumCompanionState(StrEnum):
    """The companion states this guard distinguishes.

    ``CLOSED`` is deliberately its own value rather than folded into
    ``OPEN``: a companion closed without merging is the OMN-15214 incident
    state, which no re-run can repair, so it must not read as "not yet".
    """

    MERGED = "merged"
    OPEN = "open"
    CLOSED = "closed"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class RunSnapshot:
    """The fields of an Actions run this guard reasons about."""

    run_id: int
    run_attempt: int
    name: str = ""


@dataclass(frozen=True)
class PrHealInput:
    """Everything the pure decision needs about one pull request."""

    pr_number: int
    head_sha: str
    body: str
    failed_preflight_check_count: int
    companion_state: EnumCompanionState
    companion_number: int | None
    failed_runs: tuple[RunSnapshot, ...] = ()
    #: Whether GitHub reports this PR as a draft. occ-autobind deliberately
    #: does not mint a companion for a draft (OMN-14741 F-17 suppression), so
    #: a draft with no ``Evidence-Source:`` line is expected, not missing.
    is_draft: bool = False
    #: The producer's own ``reason=`` when the ``occ-autobind / outcome``
    #: check-run for this head reports a terminal DECLINED verdict, or
    #: ``None`` when no such terminal decline was found (no check-run yet, an
    #: ERROR outcome, or a MINTED one -- all of which leave this PR on the
    #: ordinary NO_EVIDENCE_STAMP path). A DECLINED outcome (OMN-18069/
    #: OMN-18647) is a deliberate policy refusal -- the companion is not
    #: coming for this head -- and is not the same fact as "no one has
    #: written the stamp yet".
    autobind_declined_reason: str | None = None


@dataclass(frozen=True)
class HealDecision:
    """One PR's verdict.

    ``reason`` is a stable machine-readable token; ``detail`` names the PR, the
    companion and the run ids for a human reading the job log.
    """

    outcome: EnumCompanionHealOutcome
    pr_number: int
    detail: str
    run_ids: tuple[int, ...] = field(default_factory=tuple)

    @property
    def rerun(self) -> bool:
        return self.outcome is EnumCompanionHealOutcome.RERUN_REQUIRED


def parse_evidence_source(body: str) -> str | None:
    """The value of the PR body's ``Evidence-Source:`` line, or ``None``."""
    match = EVIDENCE_SOURCE_RE.search(body or "")
    if match is None:
        return None
    return match.group(1).strip()


def parse_companion_number(evidence_source: str | None) -> int | None:
    """The companion PR number in an ``OCC#<n>`` stamp, or ``None``.

    A stamp carrying a bare OCC commit SHA resolves to ``None`` on purpose: it
    names durable evidence that is already on an onex_change_control branch, so
    there is no companion left to wait for and nothing here to heal.
    """
    if not evidence_source:
        return None
    match = OCC_PR_REF_RE.match(evidence_source.strip())
    if match is None:
        return None
    return int(match.group(1))


def read_autobind_declined_reason(check_runs: list[dict[str, object]]) -> str | None:
    """The ``reason=`` of the newest terminal DECLINED autobind outcome.

    Mirrors ``check_occ_companion_merged.read_autobind_outcome`` (OMN-18069),
    narrowed to the one outcome this heal must not conflate with a missing
    stamp: DECLINED is a policy decision the producer already made and wrote
    down, and a re-run cannot change it (OMN-18647). Returns ``None`` for
    ERROR (a fault, not a decline), MINTED, or no such check-run at all --
    every one of those leaves the caller on its ordinary NO_EVIDENCE_STAMP
    path, exactly as before this function existed.
    """
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
            return None
        outcome = payload.split(None, 1)[0]
        if outcome.upper() != AUTOBIND_OUTCOME_DECLINED:
            return None
        reason = ""
        marker = "reason="
        if marker in payload:
            reason = payload.split(marker, 1)[1].strip()
        return reason or "(no reason recorded)"
    return None


def _check_runs_in_payload(payload: object) -> list[dict[str, object]]:
    """The ``check_runs`` list of one check-runs API page, or ``[]``."""
    if not isinstance(payload, dict):
        return []
    runs = payload.get("check_runs")
    if not isinstance(runs, list):
        return []
    return [entry for entry in runs if isinstance(entry, dict)]


def decide_companion_heal(pr: PrHealInput) -> HealDecision:
    """Decide whether one PR's failed runs must be re-run.

    The order of the branches is the order in which they are cheap to refuse.
    The companion state is read BEFORE any re-run is issued, so a re-run is
    only ever spent on a wait that will pass on its first poll.
    """
    where = f"PR #{pr.pr_number} (head {pr.head_sha[:12]})"

    if pr.failed_preflight_check_count == 0:
        return HealDecision(
            outcome=EnumCompanionHealOutcome.NO_FAILED_PREFLIGHT,
            pr_number=pr.pr_number,
            detail=f"{where}: no failed occ-preflight check run on this head",
        )

    evidence_source = parse_evidence_source(pr.body)
    if evidence_source is None:
        if pr.is_draft:
            return HealDecision(
                outcome=EnumCompanionHealOutcome.DRAFT_NOT_MINTED,
                pr_number=pr.pr_number,
                detail=(
                    f"{where}: preflight failed but this PR is a draft -- "
                    "occ-autobind deliberately does not mint a companion for "
                    "a draft (OMN-14741 F-17 suppression); this is not a "
                    "missing stamp and resolves itself once the PR is marked "
                    "ready for review"
                ),
            )
        if pr.autobind_declined_reason is not None:
            return HealDecision(
                outcome=EnumCompanionHealOutcome.AUTOBIND_DECLINED,
                pr_number=pr.pr_number,
                detail=(
                    f"{where}: preflight failed and occ-autobind reported a "
                    f"terminal DECLINED outcome for this head: "
                    f"{pr.autobind_declined_reason}. This is a deliberate "
                    "policy refusal, not a missing stamp -- the companion is "
                    "not coming for this head and hand-authored evidence "
                    "(OMN-15247) is the remedy, not a re-run"
                ),
            )
        return HealDecision(
            outcome=EnumCompanionHealOutcome.NO_EVIDENCE_STAMP,
            pr_number=pr.pr_number,
            detail=(
                f"{where}: preflight failed but the body carries no "
                "Evidence-Source line, so the failure is the missing stamp "
                "and not an unmerged companion"
            ),
        )

    if pr.companion_number is None:
        return HealDecision(
            outcome=EnumCompanionHealOutcome.NOT_COMPANION_FORM,
            pr_number=pr.pr_number,
            detail=(
                f"{where}: Evidence-Source is {evidence_source!r}, which is "
                "not an OCC#<n> companion reference, so there is no companion "
                "merge to have been waited for"
            ),
        )

    if pr.companion_state is EnumCompanionState.UNRESOLVED:
        return HealDecision(
            outcome=EnumCompanionHealOutcome.COMPANION_UNRESOLVED,
            pr_number=pr.pr_number,
            detail=(
                f"{where}: companion OCC#{pr.companion_number} state could not be read"
            ),
        )

    if pr.companion_state is EnumCompanionState.CLOSED:
        # Permanent, not "not yet". This is the OMN-15214 incident state and
        # no re-run repairs it; it is its own outcome so a log reader can tell
        # a PR that is waiting from one that is stuck.
        return HealDecision(
            outcome=EnumCompanionHealOutcome.COMPANION_CLOSED,
            pr_number=pr.pr_number,
            detail=(
                f"{where}: companion OCC#{pr.companion_number} was CLOSED "
                "without merging — a re-run cannot un-close it; the companion "
                "has to be reopened or re-minted"
            ),
        )

    if pr.companion_state is not EnumCompanionState.MERGED:
        return HealDecision(
            outcome=EnumCompanionHealOutcome.COMPANION_UNMERGED,
            pr_number=pr.pr_number,
            detail=(
                f"{where}: companion OCC#{pr.companion_number} is "
                f"{pr.companion_state.value}, not merged — a re-run now would "
                "spend another full budget on a fact that is still false"
            ),
        )

    if not pr.failed_runs:
        return HealDecision(
            outcome=EnumCompanionHealOutcome.NO_FAILED_RUNS,
            pr_number=pr.pr_number,
            detail=(
                f"{where}: companion OCC#{pr.companion_number} is merged but "
                "no failed workflow run remains on this head"
            ),
        )

    eligible = tuple(
        run.run_id for run in pr.failed_runs if run.run_attempt < MAX_HEAL_RUN_ATTEMPT
    )
    if not eligible:
        return HealDecision(
            outcome=EnumCompanionHealOutcome.ATTEMPT_CEILING,
            pr_number=pr.pr_number,
            detail=(
                f"{where}: every failed run is already at the "
                f"{MAX_HEAL_RUN_ATTEMPT}-attempt ceiling; refusing to re-run"
            ),
            run_ids=(),
        )

    return HealDecision(
        outcome=EnumCompanionHealOutcome.RERUN_REQUIRED,
        pr_number=pr.pr_number,
        detail=(
            f"{where}: companion OCC#{pr.companion_number} is merged; "
            f"re-running the failed jobs of {len(eligible)} run(s)"
        ),
        run_ids=eligible,
    )


def companion_state_from_payload(payload: object) -> EnumCompanionState:
    """Read a companion's state out of a ``gh pr view`` payload.

    Unreadable resolves to ``UNRESOLVED`` rather than to a guess. The caller
    then refuses the heal, which is the safe direction: a missed heal costs the
    human re-run that is happening today anyway, while a heal issued on a
    misread companion spends a full budget for nothing.
    """
    if not isinstance(payload, dict):
        return EnumCompanionState.UNRESOLVED
    state = payload.get("state")
    if not isinstance(state, str):
        return EnumCompanionState.UNRESOLVED
    normalised = state.strip().upper()
    if normalised == "MERGED":
        return EnumCompanionState.MERGED
    if normalised == "OPEN":
        return EnumCompanionState.OPEN
    if normalised == "CLOSED":
        return EnumCompanionState.CLOSED
    return EnumCompanionState.UNRESOLVED


def failed_preflight_check_count_in_payload(
    payload: object, *, markers: tuple[str, ...]
) -> int:
    """How many FAILED preflight check runs a check-runs payload carries."""
    if not isinstance(payload, dict):
        return 0
    check_runs = payload.get("check_runs")
    if not isinstance(check_runs, list):
        return 0
    count = 0
    for entry in check_runs:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        conclusion = entry.get("conclusion")
        if not isinstance(name, str) or not isinstance(conclusion, str):
            continue
        if is_preflight_job_name(name, markers=markers) and conclusion == "failure":
            count += 1
    return count


def failed_runs_in_payload(payload: object) -> tuple[RunSnapshot, ...]:
    """The failed workflow runs in an Actions runs payload.

    ``cancelled`` is deliberately excluded. ``gh run rerun --failed`` has
    nothing to re-run in a run with no failed job, and a cancelled preflight is
    the separate OMN-16322 population with its own cause.
    """
    if not isinstance(payload, dict):
        return ()
    runs = payload.get("workflow_runs")
    if not isinstance(runs, list):
        return ()
    out: list[RunSnapshot] = []
    for entry in runs:
        if not isinstance(entry, dict):
            continue
        run_id = entry.get("id")
        if not isinstance(run_id, int):
            continue
        if entry.get("conclusion") != "failure":
            continue
        attempt = entry.get("run_attempt", 1)
        name = entry.get("name", "")
        out.append(
            RunSnapshot(
                run_id=run_id,
                run_attempt=attempt if isinstance(attempt, int) else 1,
                name=name if isinstance(name, str) else "",
            )
        )
    return tuple(out)


def run_failed_on_preflight(payload: object, *, markers: tuple[str, ...]) -> bool:
    """Whether a run's jobs payload carries a FAILED preflight job.

    This is the precision control, and it is why the heal is not simply "re-run
    everything red on this head". A run can be red for a reason the companion
    merge has nothing to do with — a genuinely failing test, a broken lint.
    Re-running that spends compute to reproduce a failure that is already
    correct, and it would let the heal look like it was papering over real
    reds. Only a run whose OWN preflight job failed is in scope.

    A jobs payload that cannot be read returns ``False``: the run is left
    alone. A missed heal costs the human re-run that happens today anyway,
    while a spurious one spends a build on somebody else's red.
    """
    if not isinstance(payload, dict):
        return False
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        return False
    for entry in jobs:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        conclusion = entry.get("conclusion")
        if not isinstance(name, str) or not isinstance(conclusion, str):
            continue
        if is_preflight_job_name(name, markers=markers) and conclusion == "failure":
            return True
    return False


class GhPort(Protocol):
    """The GitHub reads and the one write this guard needs."""

    def open_pull_requests(
        self, *, repo: str
    ) -> tuple[tuple[int, str, str, bool], ...]:
        """``(number, head_sha, body, is_draft)`` for every open PR in ``repo``."""
        ...

    def failed_preflight_check_count(self, *, repo: str, head_sha: str) -> int: ...

    def companion_state(self, *, occ_repo: str, number: int) -> EnumCompanionState: ...

    def autobind_declined_reason(self, *, repo: str, head_sha: str) -> str | None:
        """The ``reason=`` of a terminal DECLINED ``occ-autobind / outcome``
        check-run for ``head_sha``, or ``None`` when none is present (no such
        check-run yet, or its outcome is ERROR/MINTED rather than DECLINED).
        """
        ...

    def failed_runs(self, *, repo: str, head_sha: str) -> tuple[RunSnapshot, ...]: ...

    def run_failed_on_preflight(self, *, repo: str, run_id: int) -> bool: ...

    def rerun_failed(self, *, repo: str, run_id: int) -> None: ...


class GhCli:
    """:class:`GhPort` over the ``gh`` binary. Fixed argv, never a shell."""

    def _json(self, args: list[str]) -> object:
        completed = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"gh {' '.join(args)} exited {completed.returncode}: "
                f"{completed.stderr.strip()}"
            )
        try:
            return json.loads(completed.stdout or "null")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"gh {' '.join(args)} returned non-JSON: {exc}") from exc

    def open_pull_requests(
        self, *, repo: str
    ) -> tuple[tuple[int, str, str, bool], ...]:
        payload = self._json(
            [
                "pr",
                "list",
                "--repo",
                repo,
                "--state",
                "open",
                "--limit",
                str(_OPEN_PR_LIMIT),
                "--json",
                "number,headRefOid,body,isDraft",
            ]
        )
        if not isinstance(payload, list):
            # A dict here is an error object from gh. Returning () would print
            # "considered 0 open PR(s)" and exit 0 -- the green-job-that-healed
            # -nothing shape this module exists to refuse.
            raise RuntimeError(
                f"gh pr list returned {type(payload).__name__}, not a list of "
                "pull requests"
            )
        out: list[tuple[int, str, str, bool]] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            number = entry.get("number")
            head = entry.get("headRefOid")
            body = entry.get("body") or ""
            is_draft = bool(entry.get("isDraft") or False)
            if isinstance(number, int) and isinstance(head, str):
                out.append(
                    (number, head, body if isinstance(body, str) else "", is_draft)
                )
        if len(out) >= _OPEN_PR_LIMIT:
            # gh caps silently. A partial pass that reads as a complete one is
            # the same failure mode as the error object above: some PR stays
            # red and the log says the sweep was clean.
            raise RuntimeError(
                f"gh pr list returned {len(out)} open PRs, at or above the "
                f"{_OPEN_PR_LIMIT} cap, so this pass would be silently "
                "partial; raise the cap rather than healing an unknown subset"
            )
        return tuple(out)

    def failed_preflight_check_count(self, *, repo: str, head_sha: str) -> int:
        payload = self._json(
            [
                "api",
                f"repos/{repo}/commits/{head_sha}/check-runs?per_page={_PAGE_SIZE}",
                "--paginate",
                "--slurp",
            ]
        )
        # `--slurp` wraps each page in a list; sum across pages.
        pages = payload if isinstance(payload, list) else [payload]
        return sum(
            failed_preflight_check_count_in_payload(page, markers=PREFLIGHT_JOB_MARKERS)
            for page in pages
        )

    def companion_state(self, *, occ_repo: str, number: int) -> EnumCompanionState:
        try:
            payload = self._json(
                ["pr", "view", str(number), "--repo", occ_repo, "--json", "state"]
            )
        except RuntimeError:
            return EnumCompanionState.UNRESOLVED
        return companion_state_from_payload(payload)

    def autobind_declined_reason(self, *, repo: str, head_sha: str) -> str | None:
        try:
            payload = self._json(
                [
                    "api",
                    f"repos/{repo}/commits/{head_sha}/check-runs?per_page={_PAGE_SIZE}",
                    "--paginate",
                    "--slurp",
                ]
            )
        except RuntimeError:
            # Fail-open on this one read only: it can only ever turn an
            # unqualified NO_EVIDENCE_STAMP into a more precise category. An
            # outage here must never block the ordinary heal path.
            return None
        pages = payload if isinstance(payload, list) else [payload]
        check_runs = [run for page in pages for run in _check_runs_in_payload(page)]
        return read_autobind_declined_reason(check_runs)

    def failed_runs(self, *, repo: str, head_sha: str) -> tuple[RunSnapshot, ...]:
        payload = self._json(
            [
                "api",
                f"repos/{repo}/actions/runs?head_sha={head_sha}&per_page={_PAGE_SIZE}",
                "--paginate",
                "--slurp",
            ]
        )
        pages = payload if isinstance(payload, list) else [payload]
        out: list[RunSnapshot] = []
        for page in pages:
            out.extend(failed_runs_in_payload(page))
        return tuple(out)

    def run_failed_on_preflight(self, *, repo: str, run_id: int) -> bool:
        try:
            payload = self._json(
                [
                    "api",
                    f"repos/{repo}/actions/runs/{run_id}/jobs?per_page={_PAGE_SIZE}",
                    "--paginate",
                    "--slurp",
                ]
            )
        except RuntimeError:
            return False
        pages = payload if isinstance(payload, list) else [payload]
        return any(
            run_failed_on_preflight(page, markers=PREFLIGHT_JOB_MARKERS)
            for page in pages
        )

    def rerun_failed(self, *, repo: str, run_id: int) -> None:
        completed = subprocess.run(
            ["gh", "run", "rerun", str(run_id), "--repo", repo, "--failed"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"gh run rerun {run_id} --failed exited "
                f"{completed.returncode}: {completed.stderr.strip()}"
            )


def collect_decisions(
    gh: GhPort, *, repo: str, occ_repo: str, only_pr: int | None = None
) -> list[HealDecision]:
    """One :class:`HealDecision` per open PR considered.

    Reads are ordered cheapest-first so the common case — an open PR with no
    failed preflight at all — costs one check-runs read and stops.
    """
    decisions: list[HealDecision] = []
    for number, head_sha, body, is_draft in gh.open_pull_requests(repo=repo):
        if only_pr is not None and number != only_pr:
            continue

        failed_checks = gh.failed_preflight_check_count(repo=repo, head_sha=head_sha)
        evidence_source = parse_evidence_source(body)
        companion_number = parse_companion_number(evidence_source)

        # Only reached for the boundary case this heal must not miscount: a
        # failed preflight with no stamp yet, on a non-draft PR. A draft is
        # resolved for free from the listing already in hand; reading the
        # autobind check-run for every other PR (which never reaches this
        # branch) would be pure waste.
        autobind_declined_reason: str | None = None
        if failed_checks and evidence_source is None and not is_draft:
            autobind_declined_reason = gh.autobind_declined_reason(
                repo=repo, head_sha=head_sha
            )

        state = EnumCompanionState.UNRESOLVED
        runs: tuple[RunSnapshot, ...] = ()
        if failed_checks and companion_number is not None:
            state = gh.companion_state(occ_repo=occ_repo, number=companion_number)
            if state is EnumCompanionState.MERGED:
                runs = tuple(
                    run
                    for run in gh.failed_runs(repo=repo, head_sha=head_sha)
                    if gh.run_failed_on_preflight(repo=repo, run_id=run.run_id)
                )

        decisions.append(
            decide_companion_heal(
                PrHealInput(
                    pr_number=number,
                    head_sha=head_sha,
                    body=body,
                    failed_preflight_check_count=failed_checks,
                    companion_state=state,
                    companion_number=companion_number,
                    failed_runs=runs,
                    is_draft=is_draft,
                    autobind_declined_reason=autobind_declined_reason,
                )
            )
        )
    return decisions


def _build_parser() -> argparse.ArgumentParser:
    """The CLI surface.

    There is deliberately no ``--force``, no ``--skip`` and no flag that
    asserts a companion's state: the merged-companion precondition is resolved
    in-process from the OCC repository on every run, and a caller-assertable
    companion state would let a caller spend a re-run on a fact this guard
    never checked. ``tests/ci/test_occ_companion_merge_heal_omn18812.py`` reads
    this parser's own option strings and fails if one appears.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name of the product repo")
    parser.add_argument(
        "--occ-repo",
        default=OCC_REPO_DEFAULT,
        help="owner/name of the change-control repo holding the companions",
    )
    parser.add_argument(
        "--pr-number",
        default="",
        help="consider only this PR; empty considers every open PR",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report the decisions without issuing any re-run",
    )
    return parser


def main(argv: list[str] | None = None, *, gh: GhPort | None = None) -> int:
    args = _build_parser().parse_args(argv)
    client: GhPort = gh if gh is not None else GhCli()

    only_pr: int | None = None
    raw_pr = (args.pr_number or "").strip()
    if raw_pr:
        try:
            only_pr = int(raw_pr)
        except ValueError:
            print(f"::error::--pr-number must be an integer, got {raw_pr!r}")  # noqa: T201
            return EXIT_ERROR

    try:
        decisions = collect_decisions(
            client, repo=args.repo, occ_repo=args.occ_repo, only_pr=only_pr
        )
    except RuntimeError as exc:
        # A heal that could not read the state it reasons about has not healed
        # anything. Reporting that as a clean no-op is the exact defect the
        # OMN-18352 heal was rebuilt to remove.
        print(f"::error::could not resolve heal state: {exc}")  # noqa: T201
        return EXIT_ERROR

    healed = 0
    failures: list[str] = []
    for decision in decisions:
        print(f"{decision.outcome.value}: {decision.detail}")  # noqa: T201
        if not decision.rerun or args.dry_run:
            continue
        for run_id in decision.run_ids:
            try:
                client.rerun_failed(repo=args.repo, run_id=run_id)
                healed += 1
                print(f"  re-ran failed jobs of run {run_id}")  # noqa: T201
            except RuntimeError as exc:
                failures.append(f"run {run_id}: {exc}")
                print(f"::warning::could not re-run run {run_id}: {exc}")  # noqa: T201

    considered = len(decisions)
    print(f"considered {considered} open PR(s); re-ran {healed} run(s)")  # noqa: T201

    if failures and healed == 0:
        # Every re-run this pass attempted failed. That is a broken heal, not a
        # quiet one, so it goes red rather than reporting a clean sweep.
        print(f"::error::every re-run attempt failed: {'; '.join(failures)}")  # noqa: T201
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
