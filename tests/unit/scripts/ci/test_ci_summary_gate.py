# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Fail-closed verdict tests for the ``CI Summary`` poller (OMN-14127).

The ``CI Summary`` required context is posted by a NO-``needs`` poller that
calls ``scripts/ci/ci_summary_gate.py``. These tests pin the fail-closed,
default-deny verdict so the required gate can never silently rubber-stamp, and
they pin core's specific gating set + soft-allowlist (e.g. the orphan "Contract
Compliance" job must be ignored while the gate "Contract Compliance Check" must
not).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.ci.ci_summary_gate import (
    EXIT_FAILURE,
    EXIT_PENDING,
    EXIT_SUCCESS,
    GATE_JOBS,
    SPEC_REQUIRED_VALIDATOR_JOBS,
    evaluate,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]


def _job(
    name: str, conclusion: str | None, *, status: str = "completed", attempt: int = 1
) -> dict:
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "run_attempt": attempt,
    }


def _all_gates(conclusion: str = "success") -> list[dict]:
    return [_job(g, conclusion) for g in GATE_JOBS]


def _all_validators(conclusion: str = "success") -> list[dict]:
    return [_job(v, conclusion) for v in SPEC_REQUIRED_VALIDATOR_JOBS]


def _all_good() -> list[dict]:
    """Baseline of a fully-green run: every aggregate gate AND every
    spec-required validator present + completed + success."""
    return _all_gates("success") + _all_validators("success")


class TestCiSummaryGate:
    def test_all_good_is_success(self) -> None:
        code, _ = evaluate(_all_good())
        assert code == EXIT_SUCCESS

    def test_gates_success_but_validators_absent_is_pending(self) -> None:
        # Aggregate gates good, but the spec-required validators have not been
        # created yet → NOT provable → PENDING (never a vacuous green).
        code, _ = evaluate(_all_gates("success"))
        assert code == EXIT_PENDING

    def test_skipped_gate_counts_as_pass(self) -> None:
        jobs = _all_good()
        jobs[0] = _job(GATE_JOBS[0], "skipped")
        code, _ = evaluate(jobs)
        assert code == EXIT_SUCCESS

    def test_gate_failure_is_failure(self) -> None:
        jobs = _all_good()
        jobs[1] = _job(GATE_JOBS[1], "failure")
        code, report = evaluate(jobs)
        assert code == EXIT_FAILURE
        assert GATE_JOBS[1] in report

    def test_gate_cancelled_is_failure(self) -> None:
        jobs = _all_good()
        jobs[2] = _job(GATE_JOBS[2], "cancelled")
        code, _ = evaluate(jobs)
        assert code == EXIT_FAILURE

    def test_missing_gate_is_pending(self) -> None:
        # One aggregate gate absent entirely → not yet provable → PENDING.
        jobs = [j for j in _all_good() if j["name"] != GATE_JOBS[-1]]
        code, _ = evaluate(jobs)
        assert code == EXIT_PENDING

    def test_gate_still_running_is_pending(self) -> None:
        jobs = _all_good()
        jobs[0] = _job(GATE_JOBS[0], None, status="in_progress")
        code, _ = evaluate(jobs)
        assert code == EXIT_PENDING

    def test_empty_run_is_pending_not_vacuous_success(self) -> None:
        # No jobs at all must never be a vacuous green.
        code, _ = evaluate([])
        assert code == EXIT_PENDING

    def test_skipped_spec_required_validator_is_failure(self) -> None:
        # LOAD-BEARING (OMN-14127): a spec-required validator that SILENTLY SKIPS
        # (path filter / dropped need) must NOT green the gate. Its covering job
        # runs unconditionally in ci.yml, so a "skipped" conclusion is a coverage
        # drop → fail-closed, even though every gate and every other validator is
        # green. Skipped is NOT "good" for a spec-required validator.
        jobs = _all_good()
        skipped = SPEC_REQUIRED_VALIDATOR_JOBS[0]
        jobs = [j for j in jobs if j["name"] != skipped]
        jobs.append(_job(skipped, "skipped"))
        code, report = evaluate(jobs)
        assert code == EXIT_FAILURE
        assert skipped in report

    def test_failed_spec_required_validator_is_failure(self) -> None:
        jobs = _all_good()
        failed = SPEC_REQUIRED_VALIDATOR_JOBS[-1]
        jobs = [j for j in jobs if j["name"] != failed]
        jobs.append(_job(failed, "failure"))
        code, report = evaluate(jobs)
        assert code == EXIT_FAILURE
        assert failed in report

    def test_absent_spec_required_validator_is_pending(self) -> None:
        # A spec-required validator not yet created → PENDING (keep polling),
        # never a vacuous green. Drop one validator from the fully-green run.
        dropped = SPEC_REQUIRED_VALIDATOR_JOBS[3]
        jobs = [j for j in _all_good() if j["name"] != dropped]
        code, _ = evaluate(jobs)
        assert code == EXIT_PENDING

    def test_in_progress_spec_required_validator_is_pending(self) -> None:
        jobs = _all_good()
        running = SPEC_REQUIRED_VALIDATOR_JOBS[2]
        jobs = [j for j in jobs if j["name"] != running]
        jobs.append(_job(running, None, status="in_progress"))
        code, _ = evaluate(jobs)
        assert code == EXIT_PENDING

    def test_leaf_failure_fails_even_before_gates_exist(self) -> None:
        # Default-deny sweep: a non-allowlisted leaf failure fails fast, even if
        # the aggregate gates have not been created yet. "Pyright Type Checking"
        # is a real quality-gate leaf in core's ci.yml.
        jobs = [_job("Pyright Type Checking", "failure")]
        code, report = evaluate(jobs)
        assert code == EXIT_FAILURE
        assert "Pyright Type Checking" in report

    def test_allowlisted_version_pin_failure_is_ignored(self) -> None:
        # "Version Pin Compliance" carries continue-on-error and is not a gate
        # need — a failure must NOT block.
        jobs = _all_good() + [_job("Version Pin Compliance", "failure")]
        code, _ = evaluate(jobs)
        assert code == EXIT_SUCCESS

    def test_allowlisted_orphan_contract_compliance_failure_is_ignored(self) -> None:
        # The orphan "Contract Compliance" job (compliance) is not gated — a
        # failure must NOT block. This must NOT be confused with the gate
        # "Contract Compliance Check".
        jobs = _all_good() + [_job("Contract Compliance", "failure")]
        code, _ = evaluate(jobs)
        assert code == EXIT_SUCCESS

    def test_gate_contract_compliance_check_failure_is_failure(self) -> None:
        # The gating "Contract Compliance Check" is distinct from the allowlisted
        # orphan "Contract Compliance"; its failure MUST block.
        assert "Contract Compliance Check" in GATE_JOBS
        jobs = _all_good()
        idx = GATE_JOBS.index("Contract Compliance Check")
        jobs[idx] = _job("Contract Compliance Check", "failure")
        code, report = evaluate(jobs)
        assert code == EXIT_FAILURE
        assert "Contract Compliance Check" in report

    def test_self_job_is_excluded(self) -> None:
        # The poller's own in-progress/failed record must not affect the verdict.
        jobs = _all_good() + [_job("CI Summary", None, status="in_progress")]
        code, _ = evaluate(jobs)
        assert code == EXIT_SUCCESS

    def test_partial_rerun_uses_latest_attempt(self) -> None:
        # Attempt 1 failed; attempt 2 re-ran the same gate and passed → SUCCESS.
        jobs = _all_good()
        jobs[0] = _job(GATE_JOBS[0], "failure", attempt=1)
        jobs.append(_job(GATE_JOBS[0], "success", attempt=2))
        code, _ = evaluate(jobs)
        assert code == EXIT_SUCCESS

    def test_stale_older_attempt_success_does_not_override_new_failure(self) -> None:
        jobs = _all_good()
        jobs[0] = _job(GATE_JOBS[0], "success", attempt=1)
        jobs.append(_job(GATE_JOBS[0], "failure", attempt=2))
        code, _ = evaluate(jobs)
        assert code == EXIT_FAILURE

    def test_neutral_conclusion_is_fail_closed(self) -> None:
        jobs = _all_good() + [_job("Some New Job", "neutral")]
        code, _ = evaluate(jobs)
        assert code == EXIT_FAILURE

    def test_spec_required_validator_jobs_match_spec(self) -> None:
        # SYNC GUARD (OMN-14127): SPEC_REQUIRED_VALIDATOR_JOBS must equal the set
        # of covering job NAMES the operator-locked rollup-coverage spec maps
        # every spec-required validator onto. A new spec-required validator added
        # to validator_jobs therefore cannot silently escape the runtime
        # completeness anchor — this test goes red until the covering job is added
        # to SPEC_REQUIRED_VALIDATOR_JOBS.
        spec = yaml.safe_load(
            (
                REPO_ROOT / "architecture-handshakes" / "validator-requirements.yaml"
            ).read_text(encoding="utf-8")
        )
        ci = yaml.safe_load(
            (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        )
        cfg = spec["model_b_rollup_enforcement"]["repos"]["omnibase_core"]
        covering_keys: set[str] = set()
        for keys in cfg["validator_jobs"].values():
            covering_keys.update(keys if isinstance(keys, list) else [keys])
        ci_jobs = ci["jobs"]
        missing_keys = sorted(k for k in covering_keys if k not in ci_jobs)
        assert not missing_keys, (
            f"validator_jobs references undefined ci.yml jobs: {missing_keys}"
        )
        covering_names = {ci_jobs[k]["name"] for k in covering_keys}
        assert set(SPEC_REQUIRED_VALIDATOR_JOBS) == covering_names, (
            "SPEC_REQUIRED_VALIDATOR_JOBS is out of sync with the rollup-coverage "
            f"spec: missing={sorted(covering_names - set(SPEC_REQUIRED_VALIDATOR_JOBS))}, "
            f"extra={sorted(set(SPEC_REQUIRED_VALIDATOR_JOBS) - covering_names)}"
        )


class TestCiSummaryGateCli:
    def _run(self, payload: object, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "scripts/ci/ci_summary_gate.py",
                "--jobs-file",
                "-",
                *extra,
            ],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

    def test_cli_success_exit_zero_bare_array(self) -> None:
        result = self._run(_all_good())
        assert result.returncode == EXIT_SUCCESS, result.stdout + result.stderr

    def test_cli_accepts_endpoint_object_form(self) -> None:
        result = self._run({"jobs": _all_good()})
        assert result.returncode == EXIT_SUCCESS, result.stdout + result.stderr

    def test_cli_failure_exit_one(self) -> None:
        jobs = _all_good()
        jobs[0] = _job(GATE_JOBS[0], "failure")
        result = self._run(jobs)
        assert result.returncode == EXIT_FAILURE

    def test_cli_pending_exit_two(self) -> None:
        result = self._run(_all_gates("success")[:-1])
        assert result.returncode == EXIT_PENDING

    def test_cli_report_only_always_exit_zero(self) -> None:
        jobs = _all_good()
        jobs[0] = _job(GATE_JOBS[0], "failure")
        result = self._run(jobs, "--report-only")
        assert result.returncode == EXIT_SUCCESS
