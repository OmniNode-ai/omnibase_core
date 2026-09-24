# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-18157: ``test_passes`` DoD items are judged by CI Summary, not in-job.

The pinned change-control runner judges a ``test_passes`` item with
``gh pr checks`` and treats every check that is not SUCCESS, SKIPPED or NEUTRAL
as a failure. Inside the Contract Compliance Check job that set always contains
the job itself, still running, so the item can never pass there. These tests pin
the two halves of the fix: the in-job run defers the item (recording it), and
CI Summary evaluates it once every other check has reached a verdict.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from scripts.ci.deferred_test_passes_gate import (
    EXIT_FAILURE,
    EXIT_PENDING,
    EXIT_SUCCESS,
    evaluate_checks,
    load_record,
    record_required,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
DRIVER = REPO_ROOT / "scripts/ci/defer_test_passes_driver.py"
GATE_MODULE = "scripts.ci.deferred_test_passes_gate"
CI_YML = REPO_ROOT / ".github/workflows/ci.yml"

NOW = datetime(2026, 9, 23, 22, 0, tzinfo=UTC)
LONG_AGO = (NOW - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
JUST_NOW = (NOW - timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

# The pinned runner's test_passes rule (onex_change_control 91f5b691,
# contract_compliance_check._check_test_passes), reproduced for the fake
# checker below so the in-job failure is exercised, not asserted.
_FAKE_CHECKER = """
import argparse
import json
import subprocess

_RESULT_PASS = "PASS"
_RESULT_WARN = "WARN"
_RESULT_BLOCK = "BLOCK"


def _check_test_passes(_check_value, _workspace, pr_number, repo):
    out = subprocess.run(
        ["gh", "pr", "checks", str(pr_number), "--repo", repo, "--json", "name,state"],
        capture_output=True, text=True, check=False,
    ).stdout
    failures = [
        c for c in json.loads(out) if c.get("state") not in ("SUCCESS", "SKIPPED", "NEUTRAL")
    ]
    if failures:
        return _RESULT_BLOCK, "Failing CI checks: " + ", ".join(c["name"] for c in failures)
    return _RESULT_PASS, "All CI checks green"


_CHECK_RUNNERS = {"test_passes": _check_test_passes}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()
    runner = _CHECK_RUNNERS.get("test_passes")
    result, detail = runner("uv run pytest tests -q", None, args.pr, args.repo)
    print(f"[{result}] test_passes: {detail}", flush=True)
    return 1 if result == _RESULT_BLOCK else 0
"""


def _tool_path(bindir: Path) -> str:
    tool_dirs = sorted(
        {
            str(Path(found).parent)
            for found in (shutil.which("bash"), shutil.which("env"))
            if found is not None
        }
    )
    return os.pathsep.join([str(bindir), *tool_dirs, "/usr/bin", "/bin"])


def _gh_stub(tmp_path: Path, script: str) -> Path:
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    gh = bindir / "gh"
    gh.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + script, encoding="utf-8")
    gh.chmod(0o755)
    return bindir


def _checker(tmp_path: Path) -> Path:
    src = tmp_path / "checker/src"
    module_dir = src / "onex_change_control/scripts"
    module_dir.mkdir(parents=True)
    (src / "onex_change_control/__init__.py").write_text("", encoding="utf-8")
    (module_dir / "__init__.py").write_text("", encoding="utf-8")
    (module_dir / "contract_compliance_check.py").write_text(
        _FAKE_CHECKER, encoding="utf-8"
    )
    return src


def _running_self_stub(tmp_path: Path) -> Path:
    """gh reports every other check green and this job's own check running."""
    return _gh_stub(
        tmp_path,
        """printf '%s\\n' '[{"name":"Tests Gate","state":"SUCCESS"},{"name":"Contract Compliance Check","state":"IN_PROGRESS"}]'\n""",
    )


# --- in-job half -------------------------------------------------------------


def test_pinned_rule_blocks_in_job_on_the_jobs_own_running_check(
    tmp_path: Path,
) -> None:
    """RED premise: run in-job, the pinned rule fails on its own running check."""
    src = _checker(tmp_path)
    bindir = _running_self_stub(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from onex_change_control.scripts import "
            "contract_compliance_check as c; sys.exit(c.main())",
            "--pr",
            "7",
            "--repo",
            "o/r",
        ],
        env={"PATH": _tool_path(bindir), "PYTHONPATH": str(src)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Failing CI checks: Contract Compliance Check" in result.stdout


def test_driver_defers_test_passes_and_records_it(tmp_path: Path) -> None:
    src = _checker(tmp_path)
    bindir = _running_self_stub(tmp_path)
    record = tmp_path / "out/record.json"
    result = subprocess.run(
        [
            sys.executable,
            str(DRIVER),
            "--deferred-record",
            str(record),
            "--",
            "--pr",
            "7",
            "--repo",
            "o/r",
        ],
        env={"PATH": _tool_path(bindir), "PYTHONPATH": str(src)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[WARN] test_passes: DEFERRED to CI Summary" in result.stdout
    payload = json.loads(record.read_text(encoding="utf-8"))
    assert payload["deferred"] == [
        {"pr_number": 7, "repo": "o/r", "check_value": "uv run pytest tests -q"}
    ]
    assert load_record(record) == payload["deferred"]


def test_driver_fails_closed_when_the_pinned_runner_table_is_absent(
    tmp_path: Path,
) -> None:
    src = _checker(tmp_path)
    module = src / "onex_change_control/scripts/contract_compliance_check.py"
    module.write_text(
        _FAKE_CHECKER.replace(
            '_CHECK_RUNNERS = {"test_passes": _check_test_passes}', ""
        ),
        encoding="utf-8",
    )
    bindir = _running_self_stub(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(DRIVER),
            "--deferred-record",
            str(tmp_path / "record.json"),
            "--",
            "--pr",
            "7",
            "--repo",
            "o/r",
        ],
        env={"PATH": _tool_path(bindir), "PYTHONPATH": str(src)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "test_passes" in result.stderr
    assert not (tmp_path / "record.json").exists()


# --- CI Summary half ---------------------------------------------------------


def _row(
    name: str,
    conclusion: str | None,
    *,
    completed: str = LONG_AGO,
    started: str = "2026-09-23T19:00:00Z",
    row_id: int = 1,
    app: str = "github-actions",
) -> dict[str, object]:
    """A ``commits/{sha}/check-runs`` row; ``conclusion=None`` is still running."""
    return {
        "id": row_id,
        "name": name,
        "app": {"slug": app},
        "status": "in_progress" if conclusion is None else "completed",
        "conclusion": conclusion,
        "started_at": started,
        "completed_at": None if conclusion is None else completed,
    }


SELF = _row("CI Summary", None)


def test_deferred_evaluation_passes_when_every_other_check_is_green() -> None:
    checks = [
        _row("Tests Gate", "success"),
        _row("CodeQL", "neutral"),
        _row("auto-tag", "skipped"),
        SELF,
    ]
    code, report = evaluate_checks(checks, now=NOW)
    assert code == EXIT_SUCCESS, report


def test_deferred_evaluation_fails_when_one_check_is_red() -> None:
    """Positive control: the same green set plus one settled red fails."""
    checks = [_row("Tests Gate", "success"), _row("verify / verify", "failure"), SELF]
    code, report = evaluate_checks(checks, now=NOW)
    assert code == EXIT_FAILURE
    assert "verify / verify" in report


def test_only_this_repos_actions_check_runs_are_ci() -> None:
    """Live on omnibase_core#1745 (CI run 35937158947): the change-control App
    posted ``occ-autobind / outcome`` as a failure ("nothing to commit") on a PR
    whose evidence was already bound and merged. An App's report is not CI; the
    evidence gates judge evidence. A row with no app is still judged."""
    app_red = [
        _row("Tests Gate", "success"),
        _row("occ-autobind / outcome", "failure", app="onexbot-occ-writer"),
    ]
    assert evaluate_checks(app_red, now=NOW)[0] == EXIT_SUCCESS
    no_app = _row("mystery", "failure")
    del no_app["app"]
    assert (
        evaluate_checks([_row("Tests Gate", "success"), no_app], now=NOW)[0]
        == EXIT_FAILURE
    )


def test_deferred_evaluation_waits_for_a_still_running_check() -> None:
    checks = [
        _row("Tests Gate", "success"),
        _row("CodeQL / CodeQL Analysis (python)", None),
        SELF,
    ]
    code, report = evaluate_checks(checks, now=NOW)
    assert code == EXIT_PENDING
    assert "CodeQL / CodeQL Analysis (python)" in report


def test_every_ci_summary_row_is_excluded() -> None:
    """CI Summary is the judge; an older or parallel CI Summary is not waited on."""
    checks = [
        _row("Tests Gate", "success"),
        _row("CI Summary", "failure", started="2026-09-23T18:00:00Z", row_id=5),
        _row("CI Summary", None, started="2026-09-23T21:00:00Z", row_id=9),
    ]
    assert evaluate_checks(checks, now=NOW)[0] == EXIT_SUCCESS


def test_same_named_rows_resolve_latest_wins() -> None:
    """A reusable called from two workflows: the newer row is the verdict."""
    red_then_green = [
        _row(
            "occ-preflight / eligibility",
            "failure",
            started="2026-09-23T19:00:00Z",
            row_id=1,
        ),
        _row(
            "occ-preflight / eligibility",
            "success",
            started="2026-09-23T19:30:00Z",
            row_id=2,
        ),
    ]
    assert evaluate_checks(red_then_green, now=NOW)[0] == EXIT_SUCCESS
    green_then_red = [
        _row(
            "occ-preflight / eligibility",
            "success",
            started="2026-09-23T19:00:00Z",
            row_id=1,
        ),
        _row(
            "occ-preflight / eligibility",
            "failure",
            started="2026-09-23T19:30:00Z",
            row_id=2,
        ),
    ]
    assert evaluate_checks(green_then_red, now=NOW)[0] == EXIT_FAILURE


def test_a_newer_skipped_row_replaces_an_older_cancelled_one() -> None:
    """Live on omnibase_core#1745 (CI run 35932440937): a cancelled run left
    ``Shadow Selection Compare`` cancelled; the rerun on the same head skipped it.
    Skipped is a pass here, so the newer skip is the verdict. (``ci_summary_gate``
    drops such a skip for its L4 contexts, where skipped is not a pass.)"""
    checks = [
        _row(
            "Shadow Selection Compare",
            "cancelled",
            started="2026-09-23T23:34:00Z",
            row_id=1,
        ),
        _row(
            "Shadow Selection Compare",
            "skipped",
            started="2026-09-24T00:05:00Z",
            row_id=2,
        ),
    ]
    assert evaluate_checks(checks, now=NOW)[0] == EXIT_SUCCESS


def test_a_fresh_cancellation_is_held_for_its_replacement() -> None:
    fresh = [_row("Enable Auto-Merge", "cancelled", completed=JUST_NOW)]
    assert evaluate_checks(fresh, now=NOW)[0] == EXIT_PENDING
    settled = [_row("Enable Auto-Merge", "cancelled")]
    assert evaluate_checks(settled, now=NOW)[0] == EXIT_FAILURE


def test_unknown_conclusion_and_empty_set_fail_closed() -> None:
    assert evaluate_checks([_row("x", "stale")], now=NOW)[0] == EXIT_FAILURE
    assert evaluate_checks([SELF], now=NOW)[0] == EXIT_FAILURE


def _job(name: str, conclusion: str | None, attempt: int = 1) -> dict[str, object]:
    return {
        "name": name,
        "status": "completed" if conclusion else "in_progress",
        "conclusion": conclusion,
        "run_attempt": attempt,
    }


def test_record_is_required_exactly_when_contract_compliance_succeeded() -> None:
    assert record_required([_job("Contract Compliance Check", "success")], 1) is True
    assert record_required([_job("Contract Compliance Check", "skipped")], 1) is False
    for jobs in ([], [_job("Contract Compliance Check", "failure")]):
        with pytest.raises(ValueError, match="Contract Compliance Check"):
            record_required(jobs, 1)


HEAD = "c" * 40


def _gh_api_script(check_runs: list[dict[str, object]], *, pr_head: str = HEAD) -> str:
    """gh stub: `gh api --paginate ... --jq ...` prints one JSON object per line."""
    lines = "\n".join(json.dumps(row) for row in check_runs)
    return (
        'case "$*" in\n'
        f"  *\"commits/{HEAD}/check-runs\"*) cat <<'JSON'\n{lines}\nJSON\n ;;\n"
        f'  *"commits/{HEAD}/status"*) : ;;\n'
        f'  *"pulls/7"*) echo {pr_head} ;;\n'
        '  *) echo "unexpected gh $*" >&2; exit 8 ;;\n'
        "esac\n"
    )


def _run_gate(
    tmp_path: Path,
    *,
    record: Path,
    gh_script: str,
    conclusion: str = "success",
    head_sha: str = HEAD,
) -> subprocess.CompletedProcess[str]:
    jobs = tmp_path / "jobs.json"
    jobs.write_text(
        json.dumps([_job("Contract Compliance Check", conclusion)]), encoding="utf-8"
    )
    bindir = _gh_stub(tmp_path, gh_script)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            GATE_MODULE,
            "--jobs-file",
            str(jobs),
            "--run-attempt",
            "1",
            "--record",
            str(record),
            "--head-sha",
            head_sha,
            "--deadline-seconds",
            "0",
            "--poll-interval-seconds",
            "0",
        ],
        cwd=REPO_ROOT,
        env={"PATH": _tool_path(bindir)},
        capture_output=True,
        text=True,
        check=False,
    )


def _write_record(tmp_path: Path, deferred: list[dict[str, object]]) -> Path:
    record = tmp_path / "record.json"
    record.write_text(json.dumps({"schema": 1, "deferred": deferred}), encoding="utf-8")
    return record


_ITEM = {"pr_number": 7, "repo": "o/r", "check_value": "pytest"}


def test_gate_cli_passes_with_green_checks_and_fails_on_a_red_one(
    tmp_path: Path,
) -> None:
    record = _write_record(tmp_path, [_ITEM])
    green = _gh_api_script([_row("Tests Gate", "success"), SELF])
    ok = _run_gate(tmp_path, record=record, gh_script=green)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    red = _gh_api_script([_row("Tests Gate", "failure"), SELF])
    bad = _run_gate(tmp_path, record=record, gh_script=red)
    assert bad.returncode == 1
    assert "Tests Gate" in bad.stdout


def test_gate_cli_resolves_the_recorded_prs_head_when_none_is_given(
    tmp_path: Path,
) -> None:
    """push runs: no pull_request head in the event, so the PR's head is judged."""
    record = _write_record(tmp_path, [_ITEM])
    green = _gh_api_script([_row("Tests Gate", "success")])
    result = _run_gate(tmp_path, record=record, gh_script=green, head_sha="")
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"at {HEAD}" in result.stdout


def test_gate_cli_fails_closed_at_the_deadline_while_a_check_is_pending(
    tmp_path: Path,
) -> None:
    record = _write_record(tmp_path, [_ITEM])
    pending = _gh_api_script([_row("CodeQL", None)])
    result = _run_gate(tmp_path, record=record, gh_script=pending)
    assert result.returncode == 1
    assert "deadline" in result.stdout


def test_gate_cli_with_nothing_deferred_never_calls_gh(tmp_path: Path) -> None:
    record = _write_record(tmp_path, [])
    result = _run_gate(tmp_path, record=record, gh_script="echo called >&2; exit 9\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "called" not in result.stderr


def test_gate_cli_fails_closed_on_a_missing_record_and_skips_when_not_required(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "absent.json"
    result = _run_gate(tmp_path, record=missing, gh_script="exit 9\n")
    assert result.returncode == 1
    assert "record" in result.stdout.lower()
    skipped = _run_gate(
        tmp_path, record=missing, gh_script="exit 9\n", conclusion="skipped"
    )
    assert skipped.returncode == 0, skipped.stdout + skipped.stderr


# --- workflow wiring ---------------------------------------------------------


def _jobs() -> dict[str, dict[str, object]]:
    return yaml.safe_load(CI_YML.read_text(encoding="utf-8"))["jobs"]


def test_contract_compliance_records_and_uploads_the_deferred_items() -> None:
    steps = _jobs()["contract-compliance"]["steps"]
    run_step = next(
        s
        for s in steps
        if s.get("name")
        == "Run DoD contract compliance against the product tree (OMN-14887)"
    )
    assert "--deferred-record" in run_step["run"]
    exempt = next(
        s
        for s in steps
        if s.get("name")
        == "Record dependency-bot workflow-only contract compliance decision"
    )
    assert "--deferred-record" not in exempt["run"]
    assert '"deferred": []' in exempt["run"]
    upload = next(s for s in steps if s.get("uses") == "actions/upload-artifact@v7")
    assert upload["with"]["name"] == "contract-compliance-deferred"
    assert upload["with"]["if-no-files-found"] == "error"
    assert upload["with"]["overwrite"] is True


def test_ci_summary_evaluates_deferred_items_after_its_verdict() -> None:
    job = _jobs()["ci-summary"]
    names = [s.get("name") for s in job["steps"]]
    poll = names.index("Poll run jobs and compute fail-closed CI Summary verdict")
    deferred = names.index("Evaluate deferred test_passes DoD items (OMN-18157)")
    assert deferred == poll + 1
    step = job["steps"][deferred]
    assert "if" not in step, "must run only when the poll step succeeded"
    assert "scripts.ci.deferred_test_passes_gate" in step["run"]
    assert "contract-compliance-deferred" in step["run"]
    assert job["permissions"]["pull-requests"] == "read"
    assert job["permissions"]["actions"] == "read"
