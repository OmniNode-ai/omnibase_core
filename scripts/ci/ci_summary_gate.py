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
    "OCC Companion Merged Gate (OMN-15214)",  # occ-companion-merged — cited OCC evidence must be MERGED before product merge (OMN-15222 port)
)

# OMN-15222 (port of the omnibase_infra OMN-15214 canary, mirroring omniclaude's
# OMN-14350 STRICT_SUCCESS_JOBS precedent): jobs that must be EXACTLY
# ``success`` — stricter than GATE_JOBS membership, whose completeness anchor
# accepts ``success``||``skipped``. Each of these runs UNCONDITIONALLY in ci.yml
# (no ``if:``, no ``needs:``), so a SKIPPED or CANCELLED conclusion is anomalous
# un-enforcement and must fail closed, not pass.
STRICT_SUCCESS_JOBS: frozenset[str] = frozenset(
    {
        "OCC Companion Merged Gate (OMN-15214)",
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
    "LLM refs drift check (OMN-11932)",
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


def _external_check_states(
    check_runs: list[dict[str, object]],
) -> dict[str, JobState]:
    """Collapse ``commits/{sha}/check-runs`` rows to one entry per check-run name.

    That endpoint has no ``run_attempt`` field like the Actions jobs endpoint —
    a rerun instead POSTs a new check-run row under the same name. Rows are
    kept by latest ``started_at`` (lexicographic ISO-8601 compare; ties keep
    array order, last wins) so a stale failed rerun can never outrank a fresh
    success, mirroring the run-attempt dedup used for in-run jobs above.
    """

    best: dict[str, tuple[str, JobState]] = {}
    for raw in check_runs:
        name = str(raw.get("name") or "")
        if not name:
            continue
        conclusion = raw.get("conclusion")
        started_at = str(raw.get("started_at") or "")
        state = JobState(
            name=name,
            status=str(raw.get("status") or ""),
            conclusion=None if conclusion is None else str(conclusion),
            run_attempt=1,
        )
        prev = best.get(name)
        if prev is None or started_at >= prev[0]:
            best[name] = (started_at, state)
    return {name: state for name, (_started_at, state) in best.items()}


def evaluate_external(
    check_runs: list[dict[str, object]],
    *,
    expected: tuple[str, ...] = EXPECTED_EXTERNAL_CONTEXTS,
) -> tuple[list[str], list[str]]:
    """Return ``(failures, missing_or_pending)`` for L4 EXPECTED_EXTERNAL_CONTEXTS.

    STRICT success-only, mirroring :data:`STRICT_SUCCESS_JOBS`: each name in
    ``expected`` must be present with ``status == 'completed'`` and
    ``conclusion == 'success'``. Absent, still-running, skipped, failed, and
    cancelled are never a silent pass — absent/still-running is
    missing-or-pending (poll again, fail-closed at the caller's deadline);
    everything else present+completed+not-success is an immediate failure.
    """

    latest = _external_check_states(check_runs)
    failures = sorted(
        name
        for name in expected
        if (st := latest.get(name)) is not None
        and st.status == "completed"
        and st.conclusion != "success"
    )
    missing_or_pending = sorted(
        name
        for name in expected
        if name not in latest or latest[name].status != "completed"
    )
    return failures, missing_or_pending


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
        external_check_runs or [], expected=external_contexts
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
) -> str:
    external_failures = external_failures or []
    external_missing_or_pending = external_missing_or_pending or []
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
    args = parser.parse_args(argv)

    jobs = _load_jobs(args.jobs_file)
    external_check_runs = _load_check_runs(args.external_check_runs_file)
    code, report = evaluate(
        jobs, run_attempt=args.run_attempt, external_check_runs=external_check_runs
    )
    print(report)  # noqa: T201 — CLI verdict report to stdout for the poll loop
    if args.report_only:
        return EXIT_SUCCESS
    return code


if __name__ == "__main__":
    raise SystemExit(main())
