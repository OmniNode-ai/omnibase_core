# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Old gate vs generic validator on recorded rows (OMN-17864 cutover parity).

The rows file is written by the very jq program the CI Summary step runs (read out of ci.yml between
its ROWS_JQ markers), from raw ``jobs`` / ``check-runs`` API rows. Both verdicts are then computed from
the same raw rows: ``scripts/ci/ci_summary_gate.evaluate`` and the ``ci_summary_verdict`` validator.
Known-bad rows must fail on both.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from omnibase_core.validation.validator_ci_summary_verdict import (
    ValidatorCiSummaryVerdict,
)
from tests.unit.validation.test_ci_summary_verdict import (
    _STRICT,
    _contract,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_NOW = datetime(2026, 9, 4, 7, 59, tzinfo=UTC)
_DEADLINE = "2026-09-04T10:08:00Z"
_spec = importlib.util.spec_from_file_location(
    "ci_summary_gate_old", _ROOT / "scripts/ci/ci_summary_gate.py"
)
assert _spec is not None and _spec.loader is not None
_old = importlib.util.module_from_spec(_spec)
sys.modules["ci_summary_gate_old"] = _old
_spec.loader.exec_module(_old)


def _jq_program() -> str:
    text = (_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    block = text.split("# ROWS_JQ_BEGIN")[1].split("# ROWS_JQ_END")[0]
    found = re.search(r"rows_jq='(.*)'\s*$", block, re.S)
    assert found is not None
    return found.group(1)


def _job(
    name: str, status: str = "completed", conclusion: str | None = "success"
) -> dict:
    return {
        "id": abs(hash(name)) % 10**6,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "run_attempt": 1,
        "started_at": "2026-09-04T07:00:00Z",
        "completed_at": "2026-09-04T07:30:00Z" if status == "completed" else None,
    }


def _check(
    name: str, conclusion: str | None, done: str, status: str = "completed", n: int = 1
) -> dict:
    return {
        "id": n,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "started_at": done,
        "completed_at": done if status == "completed" else None,
    }


def _good_jobs() -> list[dict]:
    names = [
        "Quality Gate",
        "Tests Gate",
        "Cross-repo boundary validation",
        *_STRICT,
        "lint",
    ]
    return [_job(n) for n in names]


def _good_checks() -> list[dict]:
    return [
        _check("DB ownership CI twin (B1)", "success", "2026-09-04T07:50:00Z"),
        _check(
            "advisory-job-gate / advisory-job-gate", "success", "2026-09-04T07:50:00Z"
        ),
        _check("repo-evidence / dod-verify", "success", "2026-09-04T07:50:00Z"),
    ]


def _both(
    tmp_path: Path, jobs: list[dict], checks: list[dict], event: str = "pull_request"
) -> tuple[int, int]:
    rows = subprocess.run(
        [
            "jq",
            "-n",
            "--argjson",
            "jobs",
            json.dumps([jobs]),
            "--argjson",
            "checks",
            json.dumps([checks]),
            "--arg",
            "observed",
            _NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "--arg",
            "deadline",
            _DEADLINE,
            "--arg",
            "event",
            event,
            _jq_program(),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    target = tmp_path / "ci_summary_rows.json"
    target.write_text(rows, encoding="utf-8")
    validator = ValidatorCiSummaryVerdict(_contract())
    new = validator.get_exit_code(validator.validate(target))
    old, _report = _old.evaluate(
        jobs,
        run_attempt=1,
        external_check_runs=checks,
        external_contexts=_old.external_contexts_for_event(event),
        now=_NOW,
    )
    return old, new


def test_known_good_rows_agree_green(tmp_path: Path) -> None:
    assert _both(tmp_path, _good_jobs(), _good_checks()) == (0, 0)


def test_pending_rows_agree_pending(tmp_path: Path) -> None:
    running = [
        _job("lint", "in_progress", None) if j["name"] == "lint" else j
        for j in _good_jobs()
    ]
    assert _both(tmp_path, running, _good_checks()) == (2, 2)
    absent_gate = [j for j in _good_jobs() if j["name"] != "Tests Gate"]
    assert _both(tmp_path, absent_gate, _good_checks()) == (2, 2)
    assert _both(tmp_path, _good_jobs(), _good_checks()[:2]) == (2, 2)


def test_ghost_in_progress_row_with_terminal_fields_is_done(tmp_path: Path) -> None:
    ghost = [
        dict(j, status="in_progress") if j["name"] == "lint" else j
        for j in _good_jobs()
    ]
    assert _both(tmp_path, ghost, _good_checks()) == (0, 0)


def test_known_bad_rows_agree_red(tmp_path: Path) -> None:
    failed = [
        _job("lint", conclusion="failure") if j["name"] == "lint" else j
        for j in _good_jobs()
    ]
    assert _both(tmp_path, failed, _good_checks()) == (1, 1)
    skipped = [
        _job("Code Quality", conclusion="skipped") if j["name"] == "Code Quality" else j
        for j in _good_jobs()
    ]
    assert _both(tmp_path, skipped, _good_checks()) == (1, 1)
    stale_red = _good_checks()[1:] + [
        _check("DB ownership CI twin (B1)", "failure", "2026-09-04T06:00:00Z")
    ]
    assert _both(tmp_path, _good_jobs(), stale_red) == (1, 1)
    other = _good_checks() + [
        _check("some other producer", "failure", "2026-09-04T06:00:00Z", n=9)
    ]
    assert _both(tmp_path, _good_jobs(), other) == (1, 1)


def test_unknown_event_is_refused_by_both(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _both(tmp_path, _good_jobs(), _good_checks(), event="issue_comment")
