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
    "No New os.environ Reads (OMN-13566)",  # no-new-os-environ
    "SPDX Headers",  # spdx-headers
    "Duplicate Registry Ids",  # duplicate-registry-ids (OMN-14401)
    "Hardcoded Topic Validator",  # hardcoded-topic-validator (OMN-14430)
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


def evaluate(
    jobs: list[dict[str, object]],
    *,
    run_attempt: int | None = None,
    self_name: str = SELF_JOB_NAME,
    gate_jobs: tuple[str, ...] = GATE_JOBS,
    allowlist: frozenset[str] = SOFT_ALLOWLIST,
    required_validator_jobs: tuple[str, ...] = SPEC_REQUIRED_VALIDATOR_JOBS,
) -> tuple[int, str]:
    """Return ``(exit_code, human_report)`` for the current job snapshot."""

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

    if sweep_failures or validator_not_success:
        return EXIT_FAILURE, _report(
            "FAILURE",
            latest,
            gate_jobs,
            required_validator_jobs,
            sweep_failures,
            validator_not_success,
            gate_missing_or_pending,
            validator_missing_or_pending,
        )
    if gate_missing_or_pending or validator_missing_or_pending:
        return EXIT_PENDING, _report(
            "PENDING",
            latest,
            gate_jobs,
            required_validator_jobs,
            sweep_failures,
            validator_not_success,
            gate_missing_or_pending,
            validator_missing_or_pending,
        )
    return EXIT_SUCCESS, _report(
        "SUCCESS",
        latest,
        gate_jobs,
        required_validator_jobs,
        sweep_failures,
        validator_not_success,
        gate_missing_or_pending,
        validator_missing_or_pending,
    )


def _report(
    verdict: str,
    latest: dict[str, JobState],
    gate_jobs: tuple[str, ...],
    required_validator_jobs: tuple[str, ...],
    sweep_failures: list[str],
    validator_not_success: list[str],
    gate_missing_or_pending: list[str],
    validator_missing_or_pending: list[str],
) -> str:
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
    parser.add_argument(
        "--run-attempt",
        type=int,
        default=None,
        help="Evaluate only rows for this GitHub Actions run_attempt.",
    )
    args = parser.parse_args(argv)

    jobs = _load_jobs(args.jobs_file)
    code, report = evaluate(jobs, run_attempt=args.run_attempt)
    print(report)  # noqa: T201 — CLI verdict report to stdout for the poll loop
    if args.report_only:
        return EXIT_SUCCESS
    return code


if __name__ == "__main__":
    raise SystemExit(main())
