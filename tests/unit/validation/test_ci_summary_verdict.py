# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Known-good and known-bad rows for the ``ci_summary_verdict`` generic validator (OMN-17864).

The rows files below are what the CI Summary job writes. The bad rows must be red (error), the pending
rows must be a warning, the good rows must pass. The transient-preflight sequence is the one of the
ticket: the DB ownership context failed, the PR body was repaired, the context re-ran green.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.validator_ci_summary_verdict import (
    ValidatorCiSummaryVerdict,
)

pytestmark = pytest.mark.unit

_CONTRACT = (
    Path(__file__).resolve().parents[3]
    / "src/omnibase_core/validation/contracts/ci_summary_verdict.validation.yaml"
)
_NOW = "2026-09-04T07:59:00Z"
_DEADLINE = "2026-09-04T10:08:00Z"


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))["validation"]
    return ModelValidatorSubcontract.model_validate(data)


def _job(name: str, status: str = "completed", conclusion: str = "success") -> dict:
    return {"name": name, "status": status, "conclusion": conclusion}


def _ctx(
    name: str, conclusion: str, completed_at: str, status: str = "completed"
) -> dict:
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "completed_at": completed_at,
    }


_STRICT = [
    "Runner Route (OMN-18031) / route",
    "Skip Count Ratchet (OMN-18776)",
    'Pydantic extra="forbid" Baseline One-way (OMN-19677) / anti-growth-baseline',
    "Wheel Content Parity (OMN-18865)",
    "Propagate Config Dry-run (OMN-20074)",
    "Code Quality",
    "Mypy Validation Scripts",
    "Core-Infra Boundary",
    "Enum Governance Check",
    "Naming Conventions",
    "Pydantic Patterns",
    "AI Slop Patterns",
    "Doc-Content Scan",
    "Typed Bootstrap Environment Boundary (OMN-17744)",
    "SPDX Headers",
    "Duplicate Registry Ids",
    "Hardcoded Topic Validator",
    "Runtime Identity Validator",
    "Canonical File Shape (OMN-20304)",
    "Shape-Gate Independence (OMN-20298)",
]


def _rows(**over: object) -> dict:
    base: dict = {
        "event_name": "pull_request",
        "observed_at": _NOW,
        "deadline_at": _DEADLINE,
        "jobs": [
            _job("Quality Gate"),
            _job("Tests Gate"),
            _job("Cross-repo boundary validation"),
            *[_job(n) for n in _STRICT],
            _job("lint"),
        ],
        "check_runs": [
            _ctx(
                "advisory-job-gate / advisory-job-gate",
                "success",
                "2026-09-04T07:50:00Z",
            ),
            _ctx("DB ownership CI twin (B1)", "success", "2026-09-04T07:50:00Z"),
            _ctx("repo-evidence / dod-verify", "success", "2026-09-04T07:50:00Z"),
        ],
    }
    base.update(over)
    return base


def _verdict(tmp_path: Path, rows: dict) -> tuple[int, list[str]]:
    target = tmp_path / "ci_summary_rows.json"
    target.write_text(json.dumps(rows), encoding="utf-8")
    validator = ValidatorCiSummaryVerdict(_contract())
    result = validator.validate(target)
    return validator.get_exit_code(result), [i.message for i in result.issues]


def test_known_good_rows_pass(tmp_path: Path) -> None:
    assert _verdict(tmp_path, _rows()) == (0, [])


def test_failed_job_is_red(tmp_path: Path) -> None:
    code, msgs = _verdict(
        tmp_path,
        _rows(
            jobs=[
                _job("Quality Gate"),
                _job("Tests Gate"),
                _job("lint", conclusion="failure"),
            ]
        ),
    )
    assert code == 1 and "job lint concluded failure" in msgs[0]


def test_absent_strict_job_is_pending_then_red_at_deadline(tmp_path: Path) -> None:
    jobs = [_job("lint")]
    assert _verdict(tmp_path, _rows(jobs=jobs))[0] == 2
    assert _verdict(tmp_path, _rows(jobs=jobs, observed_at=_DEADLINE))[0] == 1


def test_running_job_is_pending(tmp_path: Path) -> None:
    jobs = [
        _job("Quality Gate"),
        _job("Tests Gate"),
        _job("lint", "in_progress", "None"),
    ]
    assert _verdict(tmp_path, _rows(jobs=jobs))[0] == 2


def test_strict_job_skipped_is_red(tmp_path: Path) -> None:
    jobs = [
        dict(j, conclusion="skipped") if j["name"] == "Code Quality" else j
        for j in _rows()["jobs"]
    ]
    assert _verdict(tmp_path, _rows(jobs=jobs))[0] == 1


def test_transient_preflight_red_is_pending_not_latched(tmp_path: Path) -> None:
    """The ticket sequence: DB ownership red 40 s ago is re-polled, not a verdict."""
    runs = [
        _ctx(
            "advisory-job-gate / advisory-job-gate", "success", "2026-09-04T07:50:00Z"
        ),
        _ctx("DB ownership CI twin (B1)", "failure", "2026-09-04T07:58:20Z"),
    ]
    code, msgs = _verdict(tmp_path, _rows(check_runs=runs))
    assert code == 2 and "rerun window" in msgs[0]


def test_stable_external_red_past_window_is_red(tmp_path: Path) -> None:
    runs = [
        _ctx(
            "advisory-job-gate / advisory-job-gate", "success", "2026-09-04T07:50:00Z"
        ),
        _ctx("DB ownership CI twin (B1)", "failure", "2026-09-04T06:00:00Z"),
    ]
    assert _verdict(tmp_path, _rows(check_runs=runs))[0] == 1


def test_transient_red_at_deadline_is_red(tmp_path: Path) -> None:
    runs = [
        _ctx(
            "advisory-job-gate / advisory-job-gate", "success", "2026-09-04T07:50:00Z"
        ),
        _ctx("DB ownership CI twin (B1)", "failure", "2026-09-04T10:07:30Z"),
    ]
    assert _verdict(tmp_path, _rows(check_runs=runs, observed_at=_DEADLINE))[0] == 1


def test_repaired_rerun_supersedes_the_red(tmp_path: Path) -> None:
    runs = [
        _ctx(
            "advisory-job-gate / advisory-job-gate", "success", "2026-09-04T07:50:00Z"
        ),
        _ctx("DB ownership CI twin (B1)", "failure", "2026-09-04T07:58:20Z"),
        _ctx("DB ownership CI twin (B1)", "success", "2026-09-04T07:58:50Z"),
        _ctx("repo-evidence / dod-verify", "success", "2026-09-04T07:50:00Z"),
    ]
    assert _verdict(tmp_path, _rows(check_runs=runs)) == (0, [])


def test_missing_external_is_pending(tmp_path: Path) -> None:
    runs = [
        _ctx("advisory-job-gate / advisory-job-gate", "success", "2026-09-04T07:50:00Z")
    ]
    assert _verdict(tmp_path, _rows(check_runs=runs))[0] == 2


def test_non_supersedable_external_conclusion_is_red(tmp_path: Path) -> None:
    runs = [
        _ctx(
            "advisory-job-gate / advisory-job-gate", "success", "2026-09-04T07:50:00Z"
        ),
        _ctx("DB ownership CI twin (B1)", "skipped", "2026-09-04T07:58:20Z"),
    ]
    assert _verdict(tmp_path, _rows(check_runs=runs))[0] == 1


def test_unreadable_rows_file_is_red(tmp_path: Path) -> None:
    target = tmp_path / "ci_summary_rows.json"
    target.write_text("{not json", encoding="utf-8")
    result = ValidatorCiSummaryVerdict(_contract()).validate(target)
    assert [i.severity for i in result.issues] == [EnumSeverity.ERROR]


def test_parity_refuses_a_copy_of_the_gate(tmp_path: Path) -> None:
    copy = tmp_path / "scripts" / "ci_summary_gate.py"
    copy.parent.mkdir()
    copy.write_text('print("CI Summary verdict: FAILURE")\n', encoding="utf-8")
    result = ValidatorCiSummaryVerdict(_contract()).validate(tmp_path)
    assert [i.code for i in result.issues] == ["ci_summary_gate_parity"]


def test_parity_passes_a_repo_without_a_copy(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")
    assert ValidatorCiSummaryVerdict(_contract()).validate(tmp_path).is_valid


def test_unknown_event_fails_closed(tmp_path: Path) -> None:
    assert _verdict(tmp_path, _rows(event_name="issue_comment"))[0] == 1


def test_push_event_needs_only_the_db_ownership_context(tmp_path: Path) -> None:
    runs = [_ctx("DB ownership CI twin (B1)", "success", "2026-09-04T07:50:00Z")]
    assert _verdict(tmp_path, _rows(event_name="push", check_runs=runs)) == (0, [])


def test_required_job_skipped_is_red_but_good_conclusion_passes(tmp_path: Path) -> None:
    jobs = _rows()["jobs"]
    ok = [
        dict(j, conclusion="skipped") if j["name"] == "Quality Gate" else j
        for j in jobs
    ]
    assert _verdict(tmp_path, _rows(jobs=ok))[0] == 0
    bad = [
        dict(j, conclusion="failure") if j["name"] == "Quality Gate" else j
        for j in jobs
    ]
    assert _verdict(tmp_path, _rows(jobs=bad))[0] == 1


def test_unrelated_red_check_run_is_swept(tmp_path: Path) -> None:
    runs = _rows()["check_runs"] + [
        _ctx("some other producer", "failure", "2026-09-04T06:00:00Z")
    ]
    assert _verdict(tmp_path, _rows(check_runs=runs))[0] == 1
    running = _rows()["check_runs"] + [
        _ctx("some other producer", "failure", "2026-09-04T06:00:00Z", "in_progress")
    ]
    assert _verdict(tmp_path, _rows(check_runs=running))[0] == 2
