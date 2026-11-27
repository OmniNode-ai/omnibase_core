# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CI Summary poll: an in-run job whose conclusion is set is done (OMN-24562).

Measured on omnibase_infra run 45566676848 (pull request 6263) and run
45561122045: the job "CI Tests Gate" read status ``in_progress`` beside
conclusion ``success`` with no open step, and the poll waited on it for 30 to
80 minutes. A job whose conclusion is set counts as completed with that
conclusion; a job with no conclusion still waits, bounded by a stall window
measured from the last other job's completion.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.ci.ci_summary_gate import (
    EXIT_FAILURE,
    EXIT_PENDING,
    EXIT_SUCCESS,
    EXPECTED_EXTERNAL_CONTEXTS,
    GATE_JOBS,
    SPEC_REQUIRED_VALIDATOR_JOBS,
    evaluate,
)

NOW = datetime(2026, 11, 25, 8, 10, 0, tzinfo=UTC)
GATE = GATE_JOBS[0]

_EXTERNAL_GREEN = [
    {"name": n, "status": "completed", "conclusion": "success"}
    for n in EXPECTED_EXTERNAL_CONTEXTS
]


def evaluate_green_externals(jobs, *, run_attempt, now):
    return evaluate(
        jobs, run_attempt=run_attempt, now=now, external_check_runs=_EXTERNAL_GREEN
    )


def _job(
    name: str,
    conclusion: str | None,
    *,
    status: str = "completed",
    completed_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "run_attempt": 1,
        "completed_at": None
        if completed_at is None
        else completed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _gates(done_at: datetime, replace: dict[str, dict[str, Any]] | None = None):
    rows = {
        g: _job(g, "success", completed_at=done_at)
        for g in (*GATE_JOBS, *SPEC_REQUIRED_VALIDATOR_JOBS)
    }
    rows.update(replace or {})
    return list(rows.values())


class TestRunningRowWithConclusion:
    def test_in_progress_success_gate_is_done_and_green(self) -> None:
        jobs = _gates(
            NOW - timedelta(minutes=1),
            {GATE: _job(GATE, "success", status="in_progress")},
        )
        code, report = evaluate_green_externals(jobs, run_attempt=1, now=NOW)
        assert code == EXIT_SUCCESS, report

    def test_in_progress_failure_gate_is_red(self) -> None:
        jobs = _gates(
            NOW - timedelta(minutes=1),
            {GATE: _job(GATE, "failure", status="in_progress")},
        )
        code, report = evaluate_green_externals(jobs, run_attempt=1, now=NOW)
        assert code == EXIT_FAILURE, report

    def test_in_progress_null_gate_still_waits(self) -> None:
        jobs = _gates(
            NOW - timedelta(minutes=1),
            {GATE: _job(GATE, None, status="in_progress")},
        )
        code, report = evaluate_green_externals(jobs, run_attempt=1, now=NOW)
        assert code == EXIT_PENDING, report

    def test_in_progress_success_unregistered_job_is_done(self) -> None:
        jobs = _gates(NOW) + [_job("Some New Job", "success", status="in_progress")]
        code, report = evaluate_green_externals(jobs, run_attempt=1, now=NOW)
        assert code == EXIT_SUCCESS, report


def _poll_step() -> dict[str, Any]:
    wf = yaml.safe_load(Path(".github/workflows/ci.yml").read_text())
    for job in wf["jobs"].values():
        for step in job.get("steps", []):
            if str(step.get("name", "")).startswith("Poll run jobs and compute"):
                return step
    raise AssertionError("poll step not found")


def _stalled(jobs: list[dict[str, Any]], now: datetime, minutes: int = 45) -> str:
    env = _poll_step()["env"]
    out = subprocess.run(
        [
            "jq",
            "-r",
            "--argjson",
            "attempt",
            "1",
            "--arg",
            "self",
            "CI Summary",
            "--argjson",
            "now",
            str(int(now.timestamp())),
            "--argjson",
            "stall",
            str(minutes * 60),
            env["STALL_JQ"],
        ],
        input=json.dumps(jobs),
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


class TestStallBound:
    """The workflow step's jq names a job with no conclusion past the window."""

    @pytest.mark.parametrize("minutes", [46, 80])
    def test_gate_without_conclusion_is_named_past_the_window(
        self, minutes: int
    ) -> None:
        jobs = _gates(
            NOW - timedelta(minutes=minutes),
            {GATE: _job(GATE, None, status="in_progress")},
        )
        assert _stalled(jobs, NOW) == GATE

    def test_within_window_nothing_is_named(self) -> None:
        jobs = _gates(
            NOW - timedelta(minutes=10),
            {GATE: _job(GATE, None, status="in_progress")},
        )
        assert _stalled(jobs, NOW) == ""

    def test_in_progress_with_success_is_not_stalled(self) -> None:
        jobs = _gates(
            NOW - timedelta(minutes=80),
            {GATE: _job(GATE, "success", status="in_progress")},
        )
        assert _stalled(jobs, NOW) == ""

    def test_two_waiting_jobs_are_both_named(self) -> None:
        jobs = _gates(
            NOW - timedelta(minutes=60),
            {GATE: _job(GATE, None, status="in_progress")},
        ) + [_job("Some New Job", None, status="queued")]
        assert sorted(_stalled(jobs, NOW).split("\n")) == sorted([GATE, "Some New Job"])

    def test_the_summary_job_itself_is_never_named(self) -> None:
        jobs = _gates(NOW - timedelta(minutes=80)) + [
            _job("CI Summary", None, status="in_progress")
        ]
        assert _stalled(jobs, NOW) == ""


class TestJobsReadPagesSmall:
    def test_jobs_read_uses_small_pages_and_retries_smaller(self) -> None:
        run = _poll_step()["run"]
        assert "actions/runs/${RUN_ID}/jobs?filter=all&per_page=${jobs_page}" in run
        assert "for jobs_page in 30 10" in run
        assert "actions/runs/${RUN_ID}/jobs?filter=all&per_page=100" not in run
