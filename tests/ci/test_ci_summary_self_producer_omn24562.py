# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CI Summary never waits on its own run (OMN-24562).

RECORDED INPUTS: CI run 45589797953 of omnibase_core#2371. Every job and L4
context was ``success`` yet the gate answered PENDING (exit 2) because three
layer-5 rows -- ``Full Suite Pass Marker (OMN-19998)``,
``Integration Tests (Split ${{ matrix.split }}/4)`` and
``Tests (Split ${{ matrix.split }}/4)`` -- were ``skipped`` rows of the
cancelled draft-era ci.yml run 45589002377, held pending while a newer run of
their producer (ci.yml, run 45589797953, the polling run itself) was
unfinished: the poll waited on itself.

Rule: a row whose producer is the workflow of the run doing the polling is
judged from that run's own jobs and never held on it. A row of another
unfinished producer is still held; a skipped row with no newer run still fails
closed.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from scripts.ci.ci_summary_gate import (
    GATE_JOBS,
    SPEC_REQUIRED_VALIDATOR_JOBS,
    evaluate,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 11, 25, 9, 57, 0, tzinfo=UTC)
CI_WORKFLOW = 9001
OTHER_WORKFLOW = 9002
DRAFT_RUN = 45589002377
SELF_RUN = 45589797953
OTHER_OLD_RUN = 45589000001
OTHER_NEW_RUN = 45589800002
HEAD = "5c0c90ce21"

DRAFT_ERA_ROWS = (
    "Full Suite Pass Marker (OMN-19998)",
    "Integration Tests (Split ${{ matrix.split }}/4)",
    "Tests (Split ${{ matrix.split }}/4)",
)


def _row(name: str, run_id: int, row_id: int) -> dict[str, object]:
    return {
        "id": row_id,
        "name": name,
        "status": "completed",
        "conclusion": "skipped",
        "head_sha": HEAD,
        "started_at": "2026-11-25T08:00:00Z",
        "completed_at": "2026-11-25T08:00:01Z",
        "details_url": f"https://github.com/o/r/actions/runs/{run_id}/job/{row_id}",
    }


def _run(run_id: int, workflow_id: int, status: str) -> dict[str, object]:
    return {
        "id": run_id,
        "workflow_id": workflow_id,
        "event": "pull_request",
        "head_sha": HEAD,
        "status": status,
        "conclusion": "cancelled" if status == "completed" else None,
        "run_started_at": "2026-11-25T09:49:00Z",
    }


def _evaluate(
    rows: list[dict[str, object]], runs: list[dict[str, object]] | None
) -> tuple[int, str]:
    """The real evaluate() over a run whose every job is green (exit 0 / 1 / 2)."""
    jobs: list[dict[str, object]] = [
        {
            "name": name,
            "status": "completed",
            "conclusion": "success",
            "run_id": SELF_RUN,
        }
        for name in [*GATE_JOBS, *SPEC_REQUIRED_VALIDATOR_JOBS]
    ]
    return evaluate(
        jobs,
        external_contexts=(),
        external_check_runs=rows,
        workflow_runs=runs,
        now=NOW,
    )


def _draft_era() -> list[dict[str, object]]:
    return [_row(n, DRAFT_RUN, 1000 + i) for i, n in enumerate(DRAFT_ERA_ROWS)]


def test_recorded_draft_era_rows_of_own_workflow_are_not_held_on_own_run() -> None:
    """Known good: the recorded rows are judged from this run's jobs: SUCCESS."""
    runs = [
        _run(DRAFT_RUN, CI_WORKFLOW, "completed"),
        _run(SELF_RUN, CI_WORKFLOW, "in_progress"),
    ]
    code, report = _evaluate(_draft_era(), runs)
    assert code == 0, report


def test_unfinished_run_of_another_producer_still_holds_the_row() -> None:
    """Known bad control: a different producer's newer unfinished run holds (2)."""
    rows = [_row("Other Gate", OTHER_OLD_RUN, 2001)]
    runs = [
        _run(OTHER_OLD_RUN, OTHER_WORKFLOW, "completed"),
        _run(OTHER_NEW_RUN, OTHER_WORKFLOW, "in_progress"),
        _run(SELF_RUN, CI_WORKFLOW, "in_progress"),
    ]
    code, report = _evaluate(rows, runs)
    assert code == 2, report
    assert "Other Gate" in report


def test_skipped_row_with_no_newer_run_still_fails_closed() -> None:
    """Known bad control: nothing replaces the row, so it fails (1)."""
    rows = [_row("Other Gate", OTHER_OLD_RUN, 2001)]
    runs = [
        _run(OTHER_OLD_RUN, OTHER_WORKFLOW, "completed"),
        _run(SELF_RUN, CI_WORKFLOW, "in_progress"),
    ]
    code, report = _evaluate(rows, runs)
    assert code == 1, report
    assert "Other Gate" in report


def test_without_a_runs_list_the_own_workflow_rows_are_not_exempted() -> None:
    """Known bad control: with no provenance nothing is exempted or passed."""
    code, report = _evaluate(_draft_era(), None)
    assert code != 0, report
