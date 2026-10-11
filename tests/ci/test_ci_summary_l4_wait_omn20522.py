# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CI Summary holds an L4 red while a newer run of its producer is unfinished (OMN-20522).

WHAT IS UNDER TEST
    The REAL L4 external-context resolution in ``scripts/ci/ci_summary_gate.py``,
    imported as the module CI runs, plus the shape of the ``CI Summary`` poller
    step in ``.github/workflows/ci.yml``.

THE INCIDENT (CASE A, omnibase_core#1881, head ``4ba4fdba``, CI run 37191706046)
    ``CI Summary`` recorded ``L4 external contexts not success (coverage gap):
    DB ownership CI twin (B1): <present, not success>`` at 09:28:15Z. The row it
    read was a ``cancelled`` row (check-run 111405107275, run 37191600018) that
    was 604 s old against ``CANCELLED_SUPERSESSION_GRACE_S = 600``. The
    replacement producer run 37191705833 had been running since 09:18:02Z, but
    its ``DB ownership`` job ``needs:`` ``occ-preflight / eligibility``, which
    ran until 09:28:55Z, so the replacement's row did not exist until
    09:28:58Z. The replacement concluded ``success`` seconds later. The
    OMN-20427 suite-sibling hold cannot see it: the replacement lives in a
    DIFFERENT check suite.

CASE B (omnibase_core#1869, head ``f7402aa6``, CI run 37178554646 attempt 2)
    ``CI Summary`` recorded the same FAILURE at 05:30:38Z in 8 s. The stale row
    (check-run 111366443636) was the attempt-1 ``cancelled`` row of run
    37178554468, 30 minutes old; attempt 2 of that SAME run started at 05:30:27Z
    and its ``DB ownership`` row appeared at 05:31:26Z.

WHAT IS RECONSTRUCTED, AND WHAT IS NOT
    Every fixture row and run in ``fixtures/omn20522/`` is a public GitHub API
    row with ids and timestamps verbatim (fetched 2026-10-04; fields trimmed to
    those the gate reads). The API returns CURRENT state, so :func:`_as_of`
    re-states each row as it stood at the replay instant: a row that started
    after ``now`` is dropped, a row or run that completed after ``now`` is
    ``in_progress``. For case B the poller's own payload is not recorded in the
    job log, and the live FAILURE proves the gate did not see an unfinished
    sibling in the stale row's suite, so the in-suite ``occ-preflight`` row is
    omitted from that replay (:func:`_case_b_rows`). Nothing else is invented.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from scripts.ci import ci_summary_gate as gate
from scripts.ci.ci_summary_gate import (
    EXTERNAL_FAILURE_SUPERSESSION_GRACE_S,
    GATE_JOBS,
    SPEC_REQUIRED_VALIDATOR_JOBS,
    evaluate_external,
    provisional_external_verdicts,
)

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent / "fixtures" / "omn20522"
REPO_ROOT = Path(__file__).resolve().parents[2]
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"

DB = "DB ownership CI twin (B1)"
ADVISORY = "advisory-job-gate / advisory-job-gate"
# OMN-20074: the third pull_request L4 context (S6 part 1).
REPO_EVIDENCE = "repo-evidence / dod-verify"
CASE_A_NOW = datetime(2026, 10, 4, 9, 28, 15, tzinfo=UTC)
CASE_B_NOW = datetime(2026, 10, 4, 5, 30, 38, tzinfo=UTC)

#: Far enough past both windows that no synthetic case holds because of a grace.
LONG_AGO = datetime(2020, 1, 1, tzinfo=UTC)
SYNTH_NOW = datetime(2026, 1, 1, tzinfo=UTC)
WORKFLOW = 111
OTHER_WORKFLOW = 222


def _z(when: datetime) -> str:
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(name: str) -> list[dict[str, object]]:
    data: list[dict[str, object]] = json.loads((FIXTURES / name).read_text("utf-8"))
    return data


def _as_of(
    rows: list[dict[str, object]], runs: list[dict[str, object]], now: datetime
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Re-state current-state API rows as they stood at ``now``."""

    stamp = _z(now)
    out_rows: list[dict[str, object]] = []
    for row in rows:
        if str(row["started_at"]) > stamp:
            continue
        row = dict(row)
        if row["completed_at"] and str(row["completed_at"]) > stamp:
            row.update(status="in_progress", conclusion=None, completed_at=None)
        out_rows.append(row)
    out_runs: list[dict[str, object]] = []
    for run in runs:
        if str(run["created_at"]) > stamp:
            continue
        run = dict(run)
        if str(run["updated_at"]) > stamp:
            run.update(status="in_progress", conclusion=None)
        out_runs.append(run)
    return out_rows, out_runs


def _case_a() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    return _as_of(
        _load("case_a_check_runs.json"), _load("case_a_workflow_runs.json"), CASE_A_NOW
    )


def _case_b_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    # RECONSTRUCTED: the live FAILURE proves no unfinished sibling in the stale
    # row's suite was visible to the poller; the occ-preflight row is omitted.
    return [row for row in rows if row["name"] == DB]


def _case_b() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows, runs = _as_of(
        _load("case_b_check_runs.json"), _load("case_b_workflow_runs.json"), CASE_B_NOW
    )
    return _case_b_rows(rows), runs


def _external(
    rows: list[dict[str, object]],
    runs: list[dict[str, object]] | None,
    now: datetime,
) -> tuple[list[str], list[str]]:
    return evaluate_external(rows, expected=(DB,), now=now, workflow_runs=runs)


class TestCaseAReplay:
    def test_omn_l4_wait_case_a_replay_is_pending(self) -> None:
        rows, runs = _case_a()
        failures, pending = _external(rows, runs, CASE_A_NOW)
        assert failures == []
        assert pending == [DB]

    def test_omn_l4_wait_case_a_replay_is_reported_as_awaiting_replacement(
        self,
    ) -> None:
        rows, runs = _case_a()
        held = provisional_external_verdicts(
            rows, expected=(DB,), now=CASE_A_NOW, workflow_runs=runs
        )
        assert held == [DB]

    def test_omn_l4_wait_case_a_without_runs_keeps_todays_failure(self) -> None:
        rows, _runs = _case_a()
        failures, pending = _external(rows, None, CASE_A_NOW)
        assert failures == [DB]
        assert pending == []

    def test_omn_l4_wait_case_a_stale_row_is_the_cancelled_one(self) -> None:
        # Positive control: the replay reads the row the incident read.
        rows, _runs = _case_a()
        db_rows = [row for row in rows if row["name"] == DB]
        assert [(r["id"], r["conclusion"]) for r in db_rows] == [
            (111405107275, "cancelled")
        ]

    def test_omn_l4_wait_case_a_after_the_replacement_succeeds_it_is_green(
        self,
    ) -> None:
        later = datetime(2026, 10, 4, 9, 29, 30, tzinfo=UTC)
        rows, runs = _as_of(
            _load("case_a_check_runs.json"), _load("case_a_workflow_runs.json"), later
        )
        assert _external(rows, runs, later) == ([], [])


class TestCaseBReplay:
    def test_omn_l4_wait_case_b_replay_is_pending(self) -> None:
        rows, runs = _case_b()
        failures, pending = _external(rows, runs, CASE_B_NOW)
        assert failures == []
        assert pending == [DB]

    def test_omn_l4_wait_case_b_without_runs_keeps_todays_failure(self) -> None:
        rows, _runs = _case_b()
        failures, pending = _external(rows, None, CASE_B_NOW)
        assert failures == [DB]
        assert pending == []

    def test_omn_l4_wait_case_b_stale_row_is_the_attempt_one_cancel(self) -> None:
        rows, runs = _case_b()
        newest = max(rows, key=lambda r: (str(r["started_at"]), int(str(r["id"]))))
        assert (newest["id"], newest["conclusion"]) == (111366443636, "cancelled")
        # The replacement is the SAME run id, a later attempt.
        run = next(r for r in runs if r["id"] == 37178554468)
        assert str(newest["details_url"]).split("/runs/")[1].startswith("37178554468/")
        assert run["run_attempt"] == 2
        assert str(run["run_started_at"]) > str(newest["completed_at"])


def _stale(
    conclusion: str,
    *,
    run_id: int = 100,
    details_url: str | None | object = ...,
    completed_at: datetime = LONG_AGO,
    name: str = DB,
    suite_id: int = 1,
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": run_id * 10,
        "name": name,
        "head_sha": "c" * 40,
        "status": "completed",
        "conclusion": conclusion,
        "started_at": _z(completed_at),
        "completed_at": _z(completed_at),
        "check_suite": {"id": suite_id},
    }
    if details_url is ...:
        row["details_url"] = (
            f"https://github.com/o/r/actions/runs/{run_id}/job/{run_id * 10}"
        )
    elif details_url is not None:
        row["details_url"] = details_url
    return row


def _run(
    run_id: int,
    *,
    status: str | None = "in_progress",
    workflow_id: int = WORKFLOW,
    event: str = "pull_request",
    run_started_at: datetime | None = None,
    head_sha: str = "c" * 40,
) -> dict[str, object]:
    run: dict[str, object] = {
        "id": run_id,
        "workflow_id": workflow_id,
        "event": event,
        "head_sha": head_sha,
        "created_at": _z(run_started_at or LONG_AGO),
        "run_started_at": _z(run_started_at or LONG_AGO),
    }
    if status is not None:
        run["status"] = status
    return run


class TestOnlyAnUnfinishedNewerProducerRunHolds:
    @pytest.mark.parametrize("conclusion", ["cancelled", "failure", "skipped"])
    def test_omn_l4_wait_a_newer_unfinished_run_of_the_producer_holds(
        self, conclusion: str
    ) -> None:
        rows = [_stale(conclusion)]
        runs = [_run(100, status="completed"), _run(101)]
        assert _external(rows, runs, SYNTH_NOW) == ([], [DB])

    @pytest.mark.parametrize("status", ["queued", "in_progress", "waiting", "pending"])
    def test_omn_l4_wait_every_unfinished_status_holds(self, status: str) -> None:
        runs = [_run(100, status="completed"), _run(101, status=status)]
        assert _external([_stale("cancelled")], runs, SYNTH_NOW) == ([], [DB])

    @pytest.mark.parametrize("conclusion", ["cancelled", "failure", "skipped"])
    def test_omn_l4_wait_no_newer_unfinished_run_still_fails(
        self, conclusion: str
    ) -> None:
        runs = [_run(100, status="completed")]
        assert _external([_stale(conclusion)], runs, SYNTH_NOW) == ([DB], [])

    @pytest.mark.parametrize("conclusion", ["cancelled", "failure", "skipped"])
    def test_omn_l4_wait_an_empty_runs_list_still_fails(self, conclusion: str) -> None:
        assert _external([_stale(conclusion)], [], SYNTH_NOW) == ([DB], [])

    def test_omn_l4_wait_a_newer_run_of_a_different_workflow_does_not_hold(
        self,
    ) -> None:
        runs = [
            _run(100, status="completed"),
            _run(101, workflow_id=OTHER_WORKFLOW),
        ]
        assert _external([_stale("cancelled")], runs, SYNTH_NOW) == ([DB], [])

    def test_omn_l4_wait_a_newer_run_of_another_event_does_not_hold(self) -> None:
        runs = [_run(100, status="completed"), _run(101, event="push")]
        assert _external([_stale("cancelled")], runs, SYNTH_NOW) == ([DB], [])

    def test_omn_l4_wait_a_newer_completed_run_does_not_hold(self) -> None:
        runs = [_run(100, status="completed"), _run(101, status="completed")]
        assert _external([_stale("cancelled")], runs, SYNTH_NOW) == ([DB], [])

    def test_omn_l4_wait_an_older_unfinished_run_does_not_hold(self) -> None:
        runs = [_run(100, status="completed"), _run(99)]
        assert _external([_stale("cancelled")], runs, SYNTH_NOW) == ([DB], [])

    def test_omn_l4_wait_an_unfinished_run_on_another_head_does_not_hold(self) -> None:
        runs = [_run(100, status="completed"), _run(101, head_sha="d" * 40)]
        assert _external([_stale("cancelled")], runs, SYNTH_NOW) == ([DB], [])

    def test_omn_l4_wait_a_run_with_no_status_is_not_provably_unfinished(self) -> None:
        runs = [_run(100, status="completed"), _run(101, status=None)]
        assert _external([_stale("cancelled")], runs, SYNTH_NOW) == ([DB], [])

    def test_omn_l4_wait_the_rows_own_attempt_in_progress_does_not_hold(self) -> None:
        # Same run id, but the row concluded AFTER this attempt started: it is
        # this attempt's own answer, not a previous attempt's.
        rows = [_stale("cancelled", completed_at=datetime(2025, 6, 2, tzinfo=UTC))]
        runs = [_run(100, run_started_at=datetime(2025, 6, 1, tzinfo=UTC))]
        assert _external(rows, runs, SYNTH_NOW) == ([DB], [])

    def test_omn_l4_wait_a_later_attempt_of_the_same_run_holds(self) -> None:
        rows = [_stale("cancelled", completed_at=datetime(2025, 6, 1, tzinfo=UTC))]
        runs = [_run(100, run_started_at=datetime(2025, 6, 2, tzinfo=UTC))]
        assert _external(rows, runs, SYNTH_NOW) == ([], [DB])

    @pytest.mark.parametrize("conclusion", ["timed_out", "action_required", "neutral"])
    def test_omn_l4_wait_strict_conclusions_are_never_held(
        self, conclusion: str
    ) -> None:
        runs = [_run(100, status="completed"), _run(101)]
        assert _external([_stale(conclusion)], runs, SYNTH_NOW) == ([DB], [])


class TestUnknownProducerIdentityIsNotHeld:
    def test_omn_l4_wait_no_details_url_is_not_held(self) -> None:
        runs = [_run(100, status="completed"), _run(101)]
        rows = [_stale("cancelled", details_url=None)]
        assert _external(rows, runs, SYNTH_NOW) == ([DB], [])

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/not-a-run",
            "https://github.com/o/r/actions/runs/abc/job/1",
            "https://github.com/o/r/runs/42",
            "",
        ],
    )
    def test_omn_l4_wait_an_unparseable_details_url_is_not_held(self, url: str) -> None:
        runs = [_run(100, status="completed"), _run(101)]
        rows = [_stale("cancelled", details_url=url)]
        assert _external(rows, runs, SYNTH_NOW) == ([DB], [])

    def test_omn_l4_wait_a_run_absent_from_the_runs_list_is_not_held(self) -> None:
        # The stale row's own run is not listed, so its workflow is unknown.
        runs = [_run(101)]
        assert _external([_stale("cancelled")], runs, SYNTH_NOW) == ([DB], [])

    def test_omn_l4_wait_a_run_with_no_workflow_id_is_not_held(self) -> None:
        own = _run(100, status="completed")
        del own["workflow_id"]
        assert _external([_stale("cancelled")], [own, _run(101)], SYNTH_NOW) == (
            [DB],
            [],
        )


class TestNothingResolvesGreenButARealSuccess:
    def test_omn_l4_wait_a_held_context_is_never_in_the_success_path(self) -> None:
        runs = [_run(100, status="completed"), _run(101)]
        failures, pending = _external([_stale("cancelled")], runs, SYNTH_NOW)
        assert DB in pending
        assert DB not in failures

    @pytest.mark.parametrize("status", ["queued", "in_progress"])
    def test_omn_l4_wait_a_present_unfinished_row_stays_pending(
        self, status: str
    ) -> None:
        row = _stale("success")
        row.update(status=status, conclusion=None, completed_at=None)
        assert _external([row], [], SYNTH_NOW) == ([], [DB])
        assert _external([row], None, SYNTH_NOW) == ([], [DB])

    def test_omn_l4_wait_a_success_row_still_passes_with_or_without_runs(self) -> None:
        runs = [_run(100, status="completed"), _run(101)]
        assert _external([_stale("success")], runs, SYNTH_NOW) == ([], [])
        assert _external([_stale("success")], None, SYNTH_NOW) == ([], [])

    def test_omn_l4_wait_no_clock_leaves_the_strict_reading_failing(self) -> None:
        # A caller that supplies neither a clock nor a runs list gets today's
        # strict reading.
        assert evaluate_external([_stale("cancelled")], expected=(DB,), now=None) == (
            [DB],
            [],
        )


def _all_green_jobs() -> list[dict[str, object]]:
    names = list(GATE_JOBS) + list(SPEC_REQUIRED_VALIDATOR_JOBS)
    return [
        {"name": n, "status": "completed", "conclusion": "success", "run_attempt": 1}
        for n in names
    ]


def _green(name: str) -> dict[str, object]:
    row = _stale("success", name=name)
    row["id"] = 5_000_000
    return row


class TestGateLevelExitCodes:
    def test_omn_l4_wait_held_context_is_exit_pending_not_failure(self) -> None:
        rows = [_stale("cancelled"), _green(ADVISORY)]
        runs = [_run(100, status="completed"), _run(101)]
        code, report = gate.evaluate(
            _all_green_jobs(),
            external_check_runs=rows,
            external_contexts=(DB, ADVISORY),
            workflow_runs=runs,
            now=SYNTH_NOW,
        )
        assert code == gate.EXIT_PENDING == 2
        assert "CI Summary verdict: PENDING" in report

    def test_omn_l4_wait_unheld_context_is_exit_failure(self) -> None:
        rows = [_stale("cancelled"), _green(ADVISORY)]
        code, report = gate.evaluate(
            _all_green_jobs(),
            external_check_runs=rows,
            external_contexts=(DB, ADVISORY),
            workflow_runs=[_run(100, status="completed")],
            now=SYNTH_NOW,
        )
        assert code == gate.EXIT_FAILURE == 1
        assert "FAILURE" in report

    def test_omn_l4_wait_a_real_failure_alongside_a_held_one_still_fails(self) -> None:
        rows = [_stale("cancelled"), _stale("failure", name=ADVISORY, run_id=200)]
        runs = [_run(100, status="completed"), _run(101)]
        code, _report = gate.evaluate(
            _all_green_jobs(),
            external_check_runs=rows,
            external_contexts=(DB, ADVISORY),
            workflow_runs=runs,
            now=SYNTH_NOW,
        )
        assert code == gate.EXIT_FAILURE


class TestCliRunsFile:
    """The CLI reads ``--workflow-runs-file``; a bad file is today's behaviour."""

    def _write(self, tmp_path: Path, runs_payload: str | None) -> list[str]:
        jobs = tmp_path / "jobs.json"
        jobs.write_text(json.dumps(_all_green_jobs()), encoding="utf-8")
        external = tmp_path / "external.json"
        external.write_text(
            json.dumps([_stale("cancelled"), _green(ADVISORY)]), encoding="utf-8"
        )
        argv = [
            "--jobs-file",
            str(jobs),
            "--external-check-runs-file",
            str(external),
            "--event-name",
            "pull_request",
        ]
        if runs_payload is not None:
            runs = tmp_path / "runs.json"
            runs.write_text(runs_payload, encoding="utf-8")
            argv += ["--workflow-runs-file", str(runs)]
        return argv

    def test_omn_l4_wait_cli_held_by_a_newer_run_exits_pending(
        self, tmp_path: Path
    ) -> None:
        payload = json.dumps([_run(100, status="completed"), _run(101)])
        assert gate.main(self._write(tmp_path, payload)) == gate.EXIT_PENDING

    def test_omn_l4_wait_cli_accepts_the_raw_endpoint_object(
        self, tmp_path: Path
    ) -> None:
        payload = json.dumps(
            {"workflow_runs": [_run(100, status="completed"), _run(101)]}
        )
        assert gate.main(self._write(tmp_path, payload)) == gate.EXIT_PENDING

    def test_omn_l4_wait_cli_without_the_flag_fails_as_today(
        self, tmp_path: Path
    ) -> None:
        assert gate.main(self._write(tmp_path, None)) == gate.EXIT_FAILURE

    @pytest.mark.parametrize("payload", ["", "not json", "{", '"a string"', "42"])
    def test_omn_l4_wait_cli_unreadable_runs_file_fails_as_today(
        self, tmp_path: Path, payload: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert gate.main(self._write(tmp_path, payload)) == gate.EXIT_FAILURE
        capsys.readouterr()

    def test_omn_l4_wait_cli_missing_runs_file_fails_as_today(
        self, tmp_path: Path
    ) -> None:
        argv = self._write(tmp_path, None) + [
            "--workflow-runs-file",
            str(tmp_path / "absent.json"),
        ]
        assert gate.main(argv) == gate.EXIT_FAILURE


def _poller_script() -> str:
    workflow = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            run = step.get("run", "")
            if "ci_summary_gate.py" in run and "DEADLINE_MINUTES" in run:
                return str(run)
    raise AssertionError("CI Summary poller step not found")


class TestPollerStepShape:
    def test_omn_l4_wait_poller_fetches_the_head_workflow_runs(self) -> None:
        script = _poller_script()
        assert "actions/runs?head_sha=${COMMIT_SHA}" in script
        assert "workflow_runs.json" in script

    def test_omn_l4_wait_both_gate_invocations_pass_the_runs_file(self) -> None:
        script = _poller_script()
        invocations = [
            line
            for line in script.splitlines()
            if "scripts/ci/ci_summary_gate.py" in line
        ]
        assert len(invocations) == 2
        assert all("--workflow-runs-file workflow_runs.json" in i for i in invocations)

    def test_omn_l4_wait_a_failed_runs_fetch_does_not_abort_the_poll(self) -> None:
        # Missing runs file == today's behaviour, so the optional fetch must not
        # join the mandatory fetch_ok chain that retries forever.
        script = _poller_script()
        fetch_ok_lines = [line for line in script.splitlines() if "fetch_ok" in line]
        assert not any("workflow_runs" in line for line in fetch_ok_lines)
        assert "rm -f workflow_runs.json" in script

    def test_omn_l4_wait_the_deadline_branch_still_fails_closed(self) -> None:
        script = _poller_script()
        assert 'DEADLINE_MINUTES: "130"' in CI_YML.read_text(encoding="utf-8")
        assert 'if [ "$(date +%s)" -ge "${deadline}" ]; then' in script
        assert "reached with gating jobs still pending — failing closed" in script
        deadline_branch = script.split('-ge "${deadline}"')[1].split("fi\n")[0]
        assert "exit 1" in deadline_branch
        assert "2) : ;;" in script
        assert 'sleep "${sleep_seconds}"' in script

    def test_omn_l4_wait_the_deadline_still_converts_sustained_pending(self) -> None:
        # Gate level: a held row stays PENDING (exit 2) on every poll, and only
        # the poller's deadline turns that into FAILURE. The gate has no clock
        # input and no way to resolve a held row green, so a sustained hold can
        # only end at success or at the deadline.
        rows = [_stale("cancelled"), _green(ADVISORY)]
        runs = [_run(100, status="completed"), _run(101)]
        for _poll in range(3):
            code, _report = gate.evaluate(
                _all_green_jobs(),
                external_check_runs=rows,
                external_contexts=(DB, ADVISORY),
                workflow_runs=runs,
                now=SYNTH_NOW,
            )
            assert code == gate.EXIT_PENDING
        assert EXTERNAL_FAILURE_SUPERSESSION_GRACE_S == 1200  # window untouched


class TestPollerExecutionOmn17864:
    """Execute the shipped bash poller and real CLI, with API/clock adapters.

    The API adapter applies the workflow's actual jq projection. This catches
    omitted producer facts that tests calling evaluate() directly cannot see.
    The clock advances on sleep so deadline tests take seconds, not 130 minutes.
    """

    def _execute(
        self,
        tmp_path: Path,
        snapshots: list[tuple[list[dict[str, object]], list[dict[str, object]]]],
        *,
        failed_endpoint: str = "",
        recover_fetch: bool = False,
        stall_fetch: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        bin_path = tmp_path / "bin"
        bin_path.mkdir()
        (bin_path / "python3").symlink_to(sys.executable)
        # Keep real tools visible when installed outside the platform default
        # PATH (for example, Homebrew on macOS), without exposing the real gh.
        for tool in ("jq", "timeout"):
            executable = shutil.which(tool)
            assert executable is not None, f"poller execution requires {tool}"
            (bin_path / tool).symlink_to(executable)
        (tmp_path / "scripts").symlink_to(REPO_ROOT / "scripts")
        (tmp_path / "clock").write_text("0\n", encoding="utf-8")
        (tmp_path / "poll").write_text("0\n", encoding="utf-8")
        for index, (rows, runs) in enumerate(snapshots):
            for name, key, data in (
                ("jobs", "jobs", _all_green_jobs()),
                ("checks", "check_runs", rows),
                ("runs", "workflow_runs", runs),
            ):
                (tmp_path / f"{index}-{name}.json").write_text(
                    json.dumps({key: data}),
                    encoding="utf-8",
                )
        gh = bin_path / "gh"
        gh.write_text(
            """#!/bin/bash
set -eu
poll=$(cat "$TEST_ROOT/poll")
case "$*" in
  *'/jobs?'*) endpoint=jobs ;;
  *'/check-runs?'*) endpoint=checks ;;
  *'/actions/runs?'*) endpoint=runs ;;
  *) exit 99 ;;
esac
echo "$endpoint" >> "$TEST_ROOT/fetches"
if [ "$endpoint" = "$TEST_FAILED_ENDPOINT" ]; then
  if [ "$TEST_STALL_FETCH" = 1 ]; then
    echo 60 > "$TEST_ROOT/clock"
    sleep 2
  elif [ "$TEST_RECOVER_FETCH" = 0 ] || [ "$poll" = 0 ]; then
    exit 1
  fi
fi
last=$((TEST_SNAPSHOT_COUNT - 1))
if [ "$poll" -gt "$last" ]; then poll=$last; fi
jq "${!#}" "$TEST_ROOT/$poll-$endpoint.json"
""",
            encoding="utf-8",
        )
        gh.chmod(0o755)
        prefix = """
date() { cat "$TEST_ROOT/clock"; }
sleep() {
  local elapsed poll
  elapsed=$(cat "$TEST_ROOT/clock")
  poll=$(cat "$TEST_ROOT/poll")
  echo "$((elapsed + $1))" > "$TEST_ROOT/clock"
  echo "$((poll + 1))" > "$TEST_ROOT/poll"
}
"""
        if stall_fetch:
            # The deadline is computed before this clock advance.
            script = _poller_script().replace(
                "attempt=0", 'attempt=0\necho 59 > "$TEST_ROOT/clock"'
            )
        else:
            script = _poller_script()
        return subprocess.run(
            ["bash", "-e", "-c", prefix + script],
            cwd=tmp_path,
            env={
                "PATH": str(bin_path) + os.pathsep + os.defpath,
                "TEST_ROOT": str(tmp_path),
                "TEST_SNAPSHOT_COUNT": str(len(snapshots)),
                "TEST_FAILED_ENDPOINT": failed_endpoint,
                "TEST_RECOVER_FETCH": str(int(recover_fetch)),
                "TEST_STALL_FETCH": str(int(stall_fetch)),
                "GH_REPO": "o/r",
                "RUN_ID": "123",
                "RUN_ATTEMPT": "1",
                "COMMIT_SHA": "c" * 40,
                "EVENT_NAME": "pull_request",
                "DEADLINE_MINUTES": "1",
                "POLL_INTERVAL_SECONDS": "45",
            },
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    def test_body_repair_replacement_is_polled_to_success(self, tmp_path: Path) -> None:
        pending = (
            [_stale("failure"), _green(ADVISORY)],
            [_run(100, status="completed"), _run(101)],
        )
        repaired = (
            [_green(DB), _stale("failure"), _green(ADVISORY), _green(REPO_EVIDENCE)],
            [_run(100, status="completed"), _run(101, status="completed")],
        )
        result = self._execute(tmp_path, [pending, repaired])
        assert result.returncode == 0, result.stdout + result.stderr
        assert "CI Summary verdict: PENDING" in result.stdout
        assert "CI Summary verdict: SUCCESS" in result.stdout

    def test_a_different_event_cannot_hold_a_stable_red(self, tmp_path: Path) -> None:
        rows = [_stale("failure"), _green(ADVISORY)]
        runs = [_run(100, status="completed"), _run(101, event="push")]
        result = self._execute(tmp_path, [(rows, runs)])
        assert result.returncode == 1, result.stdout + result.stderr
        assert "CI Summary verdict: FAILURE" in result.stdout
        assert "CI Summary verdict: PENDING" not in result.stdout

    def test_sustained_preflight_hold_fails_at_the_deadline(
        self, tmp_path: Path
    ) -> None:
        rows = [_stale("failure"), _green(ADVISORY)]
        runs = [_run(100, status="completed"), _run(101)]
        result = self._execute(tmp_path, [(rows, runs)])
        assert result.returncode == 1, result.stdout + result.stderr
        assert "poll deadline" in result.stdout
        assert (tmp_path / "clock").read_text().strip() == "60"

    @pytest.mark.parametrize("endpoint", ["jobs", "checks"])
    def test_unreadable_inputs_fail_at_the_deadline(
        self, tmp_path: Path, endpoint: str
    ) -> None:
        result = self._execute(tmp_path, [([], [])], failed_endpoint=endpoint)
        assert result.returncode == 1, result.stdout + result.stderr
        assert "poll deadline" in result.stdout
        assert (tmp_path / "clock").read_text().strip() == "60"

    def test_transient_api_failure_recovers(self, tmp_path: Path) -> None:
        result = self._execute(
            tmp_path,
            [([_green(DB), _green(ADVISORY), _green(REPO_EVIDENCE)], [])],
            failed_endpoint="checks",
            recover_fetch=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "gh api fetch failed" in result.stdout
        assert "CI Summary verdict: SUCCESS" in result.stdout

    def test_api_fetch_cannot_outlast_the_remaining_budget(
        self, tmp_path: Path
    ) -> None:
        result = self._execute(
            tmp_path, [([], [])], failed_endpoint="jobs", stall_fetch=True
        )
        assert result.returncode == 1, result.stdout + result.stderr
        assert "poll deadline" in result.stdout
