# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A re-run of only the failed jobs must be able to turn ``CI Summary`` green.

Measured on omnibase_core dev ``cd128b790ec6``: the scheduled ``ci.yml`` run
42578572957 failed 4 of its 40 test splits in attempt 1. Attempt 2 re-ran only
the failed jobs (the splits, ``Tests Gate``, ``CI Summary`` and their
dependents). GitHub keeps every job that passed in attempt 1 on its attempt-1
row (``run_attempt: 1``), so the attempt-2 poller, which passes
``--run-attempt 2``, saw no ``Quality Gate`` and none of the spec-required
validators. Those read "missing or pending", the poll stayed PENDING for the
whole 130 minute window and ``CI Summary`` failed closed with every test green.

A job that passed in an earlier attempt and was not re-run is the answer for
this attempt. Only a ``success`` row carries over; a failed, cancelled or
skipped row from an earlier attempt never does, so a job that is being re-run
and has no attempt row yet still reads pending.
"""

from __future__ import annotations

from scripts.ci.ci_summary_gate import (
    EXIT_FAILURE,
    EXIT_PENDING,
    EXIT_SUCCESS,
    GATE_JOBS,
    SPEC_REQUIRED_VALIDATOR_JOBS,
    evaluate,
)


def _job(name: str, conclusion: str, attempt: int) -> dict:
    return {
        "name": name,
        "status": "completed",
        "conclusion": conclusion,
        "run_attempt": attempt,
    }


def _names() -> list[str]:
    return [*GATE_JOBS, *SPEC_REQUIRED_VALIDATOR_JOBS]


def test_failed_only_rerun_passes_on_carried_over_successes() -> None:
    """Attempt 1: one gate failed. Attempt 2 re-ran only that gate: SUCCESS."""
    names = _names()
    rerun = GATE_JOBS[1]
    jobs = [_job(n, "failure" if n == rerun else "success", 1) for n in names]
    jobs.append(_job(rerun, "success", 2))
    code, report = evaluate(jobs, run_attempt=2, external_contexts=())
    assert code == EXIT_SUCCESS, report


def test_failed_only_rerun_still_fails_when_the_rerun_fails() -> None:
    names = _names()
    rerun = GATE_JOBS[1]
    jobs = [_job(n, "failure" if n == rerun else "success", 1) for n in names]
    jobs.append(_job(rerun, "failure", 2))
    code, report = evaluate(jobs, run_attempt=2, external_contexts=())
    assert code == EXIT_FAILURE, report
    assert rerun in report


def test_failed_job_of_an_earlier_attempt_is_not_carried_over() -> None:
    """A job that failed in attempt 1 and has no attempt-2 row is pending."""
    names = _names()
    missing = GATE_JOBS[1]
    jobs = [_job(n, "failure" if n == missing else "success", 1) for n in names]
    code, report = evaluate(jobs, run_attempt=2, external_contexts=())
    assert code == EXIT_PENDING, report
    assert missing in report


def test_cancelled_job_of_an_earlier_attempt_is_not_carried_over() -> None:
    names = _names()
    missing = SPEC_REQUIRED_VALIDATOR_JOBS[0]
    jobs = [_job(n, "cancelled" if n == missing else "success", 1) for n in names]
    code, report = evaluate(jobs, run_attempt=2, external_contexts=())
    assert code == EXIT_PENDING, report
    assert missing in report


def test_skipped_job_of_an_earlier_attempt_is_not_carried_over() -> None:
    """Only success carries: a skipped attempt-1 gate was not an answer."""
    names = _names()
    missing = GATE_JOBS[0]
    jobs = [_job(n, "skipped" if n == missing else "success", 1) for n in names]
    code, report = evaluate(jobs, run_attempt=2, external_contexts=())
    assert code == EXIT_PENDING, report
    assert missing in report


def test_current_attempt_row_wins_over_an_earlier_success() -> None:
    """A rerun that now fails is not hidden by its earlier attempt's success."""
    names = _names()
    jobs = [_job(n, "success", 1) for n in names]
    jobs.append(_job(GATE_JOBS[1], "failure", 2))
    code, report = evaluate(jobs, run_attempt=2, external_contexts=())
    assert code == EXIT_FAILURE, report
    assert GATE_JOBS[1] in report


def test_only_the_current_attempt_row_is_judged_for_a_rerun_job() -> None:
    """An attempt-2 row in progress is pending even with an attempt-1 success."""
    names = _names()
    jobs = [_job(n, "success", 1) for n in names]
    jobs.append(
        {
            "name": GATE_JOBS[1],
            "status": "in_progress",
            "conclusion": None,
            "run_attempt": 2,
        }
    )
    code, report = evaluate(jobs, run_attempt=2, external_contexts=())
    assert code == EXIT_PENDING, report


def test_newest_earlier_attempt_decides_the_carry_over() -> None:
    """Attempt 1 passed, attempt 2 failed, attempt 3 has no row yet: pending."""
    names = _names()
    stale = GATE_JOBS[1]
    jobs = [_job(n, "success", 1) for n in names]
    jobs.append(_job(stale, "failure", 2))
    jobs.extend(_job(n, "success", 3) for n in names if n != stale)
    code, report = evaluate(jobs, run_attempt=3, external_contexts=())
    assert code == EXIT_PENDING, report
    assert stale in report
