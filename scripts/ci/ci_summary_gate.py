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

# Conclusions that count as "provably passed".
GOOD_CONCLUSIONS: frozenset[str] = frozenset({"success", "skipped"})

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


def dedup_latest(jobs: list[dict[str, object]]) -> dict[str, JobState]:
    """Collapse the raw ``/runs/{id}/jobs`` array to one entry per job name.

    Uses the highest ``run_attempt`` so partial re-runs (``gh run rerun
    --failed``, which re-runs a subset in a new attempt) evaluate the freshest
    conclusion for each job while still seeing jobs that passed in an earlier
    attempt (fetch the endpoint with ``?filter=all``).
    """

    latest: dict[str, JobState] = {}
    for raw in jobs:
        name = str(raw.get("name") or "")
        if not name:
            continue
        raw_attempt = raw.get("run_attempt")
        try:
            attempt = int(raw_attempt) if isinstance(raw_attempt, (int, str)) else 1
        except (TypeError, ValueError):
            attempt = 1
        prev = latest.get(name)
        if prev is not None and attempt < prev.run_attempt:
            continue
        conclusion = raw.get("conclusion")
        latest[name] = JobState(
            name=name,
            status=str(raw.get("status") or ""),
            conclusion=None if conclusion is None else str(conclusion),
            run_attempt=attempt,
        )
    return latest


def evaluate(
    jobs: list[dict[str, object]],
    *,
    self_name: str = SELF_JOB_NAME,
    gate_jobs: tuple[str, ...] = GATE_JOBS,
    allowlist: frozenset[str] = SOFT_ALLOWLIST,
) -> tuple[int, str]:
    """Return ``(exit_code, human_report)`` for the current job snapshot."""

    latest = dedup_latest(jobs)

    # (1) Default-deny failure sweep over every present+completed job.
    sweep_failures = sorted(
        j.name
        for name, j in latest.items()
        if name != self_name
        and name not in allowlist
        and j.status == "completed"
        and j.conclusion not in GOOD_CONCLUSIONS
    )

    # (2) Completeness anchor over the aggregate gates.
    gate_missing_or_pending = [
        g
        for g in gate_jobs
        if (latest.get(g) is None or latest[g].status != "completed")
    ]

    if sweep_failures:
        return EXIT_FAILURE, _report(
            "FAILURE",
            latest,
            gate_jobs,
            allowlist,
            sweep_failures,
            gate_missing_or_pending,
        )
    if gate_missing_or_pending:
        return EXIT_PENDING, _report(
            "PENDING",
            latest,
            gate_jobs,
            allowlist,
            sweep_failures,
            gate_missing_or_pending,
        )
    return EXIT_SUCCESS, _report(
        "SUCCESS", latest, gate_jobs, allowlist, sweep_failures, gate_missing_or_pending
    )


def _report(
    verdict: str,
    latest: dict[str, JobState],
    gate_jobs: tuple[str, ...],
    allowlist: frozenset[str],
    sweep_failures: list[str],
    gate_missing_or_pending: list[str],
) -> str:
    lines = [f"CI Summary verdict: {verdict}", f"  jobs observed: {len(latest)}"]
    lines.append("  aggregate gates:")
    for g in gate_jobs:
        st = latest.get(g)
        if st is None:
            lines.append(f"    - {g}: <absent>")
        else:
            lines.append(f"    - {g}: {st.status}/{st.conclusion}")
    if sweep_failures:
        lines.append(f"  default-deny sweep failures: {', '.join(sweep_failures)}")
    if gate_missing_or_pending:
        lines.append(f"  gates missing/pending: {', '.join(gate_missing_or_pending)}")
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
    args = parser.parse_args(argv)

    jobs = _load_jobs(args.jobs_file)
    code, report = evaluate(jobs)
    print(report)  # noqa: T201 — CLI verdict report to stdout for the poll loop
    if args.report_only:
        return EXIT_SUCCESS
    return code


if __name__ == "__main__":
    raise SystemExit(main())
