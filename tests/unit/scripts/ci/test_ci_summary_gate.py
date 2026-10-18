# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Fail-closed verdict tests for the ``CI Summary`` poller (OMN-14127).

The ``CI Summary`` required context is posted by a NO-``needs`` poller that
calls ``scripts/ci/ci_summary_gate.py``. These tests pin the fail-closed,
default-deny verdict so the required gate can never silently rubber-stamp, and
they pin core's specific gating set + soft-allowlist (e.g. the orphan "Contract
Compliance" job must be ignored).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from scripts.ci import ci_summary_gate as gate
from scripts.ci.ci_summary_gate import (
    EXIT_FAILURE,
    EXIT_PENDING,
    EXIT_SUCCESS,
    EXPECTED_EXTERNAL_CONTEXTS,
    EXTERNAL_CONTEXTS_BY_EVENT,
    GATE_JOBS,
    SOFT_ALLOWLIST,
    SPEC_REQUIRED_VALIDATOR_JOBS,
    STRICT_SUCCESS_JOBS,
    drop_superseded_skips,
    evaluate,
    evaluate_external,
    external_contexts_for_event,
    provisional_external_verdicts,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
CI_YML = WORKFLOWS_DIR / "ci.yml"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

EXTERNAL_CONTEXT_PRODUCER_WORKFLOWS: dict[str, str] = {
    "DB ownership CI twin (B1)": "check-db-ownership.yml",
    "advisory-job-gate / advisory-job-gate": "advisory-job-gate.yml",
    # OMN-20074: produced on pull_request_target, see PRODUCER_TRIGGER_ALIASES.
    "repo-evidence / dod-verify": "call-repo-evidence-gate.yml",
}

# A producer trigger that reports on the same pull request head as a CI event:
# pull_request_target runs the base-branch definition for the PR head, so its
# check-run lands on the head a pull_request CI Summary run judges.
PRODUCER_TRIGGER_ALIASES: dict[str, str] = {"pull_request_target": "pull_request"}


def _job(
    name: str,
    conclusion: str | None,
    *,
    status: str = "completed",
    attempt: int = 1,
    completed_at: str | None = None,
) -> dict:
    row = {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "run_attempt": attempt,
    }
    if completed_at is not None:
        row["completed_at"] = completed_at
    return row


def _check_run(
    name: str,
    conclusion: str | None,
    *,
    status: str = "completed",
    started_at: str = "",
    head_sha: str = "",
    completed_at: str | None = None,
) -> dict:
    """Build a ``commits/{sha}/check-runs`` row (L4 external-context fixture)."""
    row = {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "started_at": started_at,
        "head_sha": head_sha,
    }
    if completed_at is not None:
        row["completed_at"] = completed_at
    return row


def _all_gates(conclusion: str = "success") -> list[dict]:
    return [_job(g, conclusion) for g in GATE_JOBS]


def _all_validators(conclusion: str = "success") -> list[dict]:
    return [_job(v, conclusion) for v in SPEC_REQUIRED_VALIDATOR_JOBS]


def _all_good() -> list[dict]:
    """Baseline of a fully-green run: every aggregate gate AND every
    spec-required validator present + completed + success."""
    return _all_gates("success") + _all_validators("success")


# L4 EXPECTED_EXTERNAL_CONTEXTS all-green fixture. Every test below this point
# predates the L4 layer and exercises in-run gate/validator/sweep behavior
# only; passing this keeps those tests' original SUCCESS/FAILURE/PENDING
# intent unchanged. Tests that specifically exercise the L4 layer itself live
# in TestExpectedExternalContexts and control external_check_runs directly.
_ALL_EXTERNAL_GREEN = [_check_run(n, "success") for n in EXPECTED_EXTERNAL_CONTEXTS]


class TestGhostRunningRowWithConclusionOmn19998:
    """Ghost running rows need both a conclusion and completion timestamp."""

    def test_ghost_success_passes(self) -> None:
        jobs = _all_good() + [
            _job(
                "Doc-Content Scan",
                "success",
                status="in_progress",
                completed_at="2026-10-16T07:54:33Z",
            )
        ]
        code, report = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_SUCCESS, report
        assert "still running" not in report

    def test_ghost_failure_fails_default_deny_sweep(self) -> None:
        jobs = _all_good() + [
            _job(
                "Doc-Content Scan",
                "failure",
                status="in_progress",
                completed_at="2026-10-16T07:54:33Z",
            )
        ]
        code, report = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_FAILURE, report
        assert "default-deny sweep failures: Doc-Content Scan" in report

    def test_success_without_completed_at_stays_pending(self) -> None:
        jobs = _all_good() + [_job("Doc-Content Scan", "success", status="in_progress")]
        code, report = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_PENDING, report
        assert "default-deny sweep rows still running" in report

    def test_completed_at_without_conclusion_stays_pending(self) -> None:
        jobs = _all_good() + [
            _job(
                "Doc-Content Scan",
                None,
                status="in_progress",
                completed_at="2026-10-16T07:54:33Z",
            )
        ]
        code, report = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_PENDING, report
        assert "default-deny sweep rows still running" in report

    def test_ghost_required_validator_success_passes(self) -> None:
        name = SPEC_REQUIRED_VALIDATOR_JOBS[0]
        jobs = [job for job in _all_good() if job["name"] != name] + [
            _job(
                name,
                "success",
                status="in_progress",
                completed_at="2026-10-16T07:54:33Z",
            )
        ]
        code, report = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_SUCCESS, report

    def test_ghost_external_context_success_passes(self) -> None:
        code, report = evaluate(_all_good(), external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_SUCCESS, report
        name = EXPECTED_EXTERNAL_CONTEXTS[0]
        checks = [row for row in _ALL_EXTERNAL_GREEN if row["name"] != name] + [
            _check_run(
                name,
                "success",
                status="in_progress",
                completed_at="2026-10-16T07:54:33Z",
            )
        ]
        code, report = evaluate(_all_good(), external_check_runs=checks)
        assert code == EXIT_SUCCESS, report


class TestRunningRowsHoldTheVerdictOmn20066:
    """In-run rows without a verdict must hold CI Summary at PENDING."""

    @pytest.mark.parametrize("status", ["queued", "in_progress", "waiting", "pending"])
    def test_running_unregistered_job_cannot_conclude_success(
        self, status: str
    ) -> None:
        """Every running status holds an otherwise passing snapshot."""
        jobs = _all_good() + [_job("Some New Job", None, status=status)]
        code, report = evaluate(
            jobs, run_attempt=1, external_check_runs=_ALL_EXTERNAL_GREEN
        )
        assert code == EXIT_PENDING, report
        assert (
            "  default-deny sweep rows still running (PENDING, re-polled): Some New Job"
            in report
        )

    @pytest.mark.parametrize("status", ["queued", "in_progress", "waiting", "pending"])
    def test_merge_group_running_unregistered_job_holds_pending(
        self, status: str
    ) -> None:
        """Merge-group's external-context tier also waits for in-run rows."""
        jobs = _all_good() + [_job("Some New Job", None, status=status)]
        code, report = evaluate(
            jobs,
            run_attempt=1,
            external_contexts=external_contexts_for_event("merge_group"),
        )
        assert code == EXIT_PENDING, report
        assert "Some New Job" in report

    def test_running_job_then_completed_success_concludes_success(self) -> None:
        """A successful completion clears the running row's pending verdict."""
        jobs = _all_good() + [_job("Some New Job", None, status="in_progress")]
        code, report = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_PENDING, report
        jobs[-1] = _job("Some New Job", "success")
        code, report = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_SUCCESS, report
        assert "default-deny sweep rows still running" not in report

    def test_running_job_then_completed_failure_fails(self) -> None:
        """A failed completion remains a default-deny sweep failure."""
        jobs = _all_good() + [_job("Some New Job", None, status="in_progress")]
        code, report = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_PENDING, report
        jobs[-1] = _job("Some New Job", "failure")
        code, report = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_FAILURE, report
        assert "default-deny sweep failures: Some New Job" in report
        assert "default-deny sweep rows still running" not in report

    def test_failure_wins_over_a_running_row(self) -> None:
        """A completed failure takes precedence over an undecided row."""
        jobs = _all_good() + [
            _job("Failed New Job", "failure"),
            _job("Some New Job", None, status="in_progress"),
        ]
        code, report = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_FAILURE, report
        assert "default-deny sweep failures: Failed New Job" in report

    @pytest.mark.parametrize("name", [*sorted(SOFT_ALLOWLIST), "CI Summary"])
    def test_allowlisted_running_rows_do_not_hold(self, name: str) -> None:
        """Advisory rows and the poller itself stay exempt."""
        jobs = _all_good() + [_job(name, None, status="in_progress")]
        code, report = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_SUCCESS, report
        assert "default-deny sweep rows still running" not in report

    def test_every_job_needing_ci_summary_is_allowlisted(self) -> None:
        """Jobs waiting directly on CI Summary must not deadlock its poller."""
        workflow = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))
        for job_id, job in workflow["jobs"].items():
            needs = job.get("needs", [])
            if isinstance(needs, str):
                needs = [needs]
            if "ci-summary" in needs:
                display_name = job.get("name") or job_id
                assert display_name in SOFT_ALLOWLIST, display_name

    def test_same_attempt_running_duplicate_is_not_hidden_by_success(self) -> None:
        jobs = _all_good() + [
            _job("Duplicate Job", None, status="in_progress"),
            _job("Duplicate Job", "success"),
        ]
        code, report = evaluate(
            jobs, run_attempt=1, external_check_runs=_ALL_EXTERNAL_GREEN
        )
        assert code == EXIT_PENDING, report
        assert (
            "default-deny sweep rows still running (PENDING, re-polled): Duplicate Job"
            in report
        )

    @pytest.mark.parametrize("run_attempt", [None, 2])
    def test_older_attempt_running_row_is_ignored(
        self, run_attempt: int | None
    ) -> None:
        jobs = _all_good() + [
            _job("Some New Job", None, status="in_progress", attempt=1),
            _job("Some New Job", "success", attempt=2),
        ]
        if run_attempt is not None:
            jobs = [dict(job, run_attempt=2) for job in _all_good()] + jobs[-2:]
        code, report = evaluate(
            jobs, run_attempt=run_attempt, external_check_runs=_ALL_EXTERNAL_GREEN
        )
        assert code == EXIT_SUCCESS, report
        assert "default-deny sweep rows still running" not in report

    def test_running_rows_are_reported_once_in_sorted_order(self) -> None:
        jobs = _all_good() + [
            _job("Z Job", None, status="queued"),
            _job("A Job", None, status="in_progress"),
            _job("A Job", None, status="waiting"),
        ]
        code, report = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_PENDING, report
        assert (
            "  default-deny sweep rows still running (PENDING, re-polled): A Job, Z Job"
            in report
        )


class TestCiSummaryGate:
    def test_all_good_is_success(self) -> None:
        code, _ = evaluate(_all_good(), external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_SUCCESS

    def test_gates_success_but_validators_absent_is_pending(self) -> None:
        # Aggregate gates good, but the spec-required validators have not been
        # created yet → NOT provable → PENDING (never a vacuous green).
        code, _ = evaluate(_all_gates("success"))
        assert code == EXIT_PENDING

    def test_skipped_gate_counts_as_pass(self) -> None:
        jobs = _all_good()
        jobs[0] = _job(GATE_JOBS[0], "skipped")
        code, _ = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
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

    def test_allowlisted_orphan_contract_compliance_failure_is_ignored(self) -> None:
        # The orphan "Contract Compliance" job (compliance) is not gated — a
        # failure must NOT block.
        jobs = _all_good() + [_job("Contract Compliance", "failure")]
        code, _ = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_SUCCESS

    def test_report_only_shadow_selection_failure_is_ignored(self) -> None:
        # The comparison only uploads a counterfactual selection record. It has
        # no pass/fail policy and is intentionally continue-on-error, so the
        # required CI Summary must not turn this report-only surface into a gate.
        jobs = _all_good() + [_job("Shadow Selection Compare", "failure")]
        code, _ = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_SUCCESS

    def test_self_job_is_excluded(self) -> None:
        # The poller's own in-progress/failed record must not affect the verdict.
        jobs = _all_good() + [_job("CI Summary", None, status="in_progress")]
        code, _ = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_SUCCESS

    def test_partial_rerun_uses_latest_attempt(self) -> None:
        # Attempt 1 failed; attempt 2 re-ran the same gate and passed → SUCCESS.
        jobs = _all_good()
        jobs[0] = _job(GATE_JOBS[0], "failure", attempt=1)
        jobs.append(_job(GATE_JOBS[0], "success", attempt=2))
        code, _ = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_SUCCESS

    def test_stale_older_attempt_success_does_not_override_new_failure(self) -> None:
        jobs = _all_good()
        jobs[0] = _job(GATE_JOBS[0], "success", attempt=1)
        jobs.append(_job(GATE_JOBS[0], "failure", attempt=2))
        code, _ = evaluate(jobs)
        assert code == EXIT_FAILURE

    def test_same_attempt_duplicate_failure_is_not_hidden_by_success(self) -> None:
        jobs = _all_good()
        jobs.extend(
            [
                _job("Duplicate Job", "failure", attempt=2),
                _job("Duplicate Job", "success", attempt=2),
            ]
        )
        code, report = evaluate(jobs, run_attempt=2)
        assert code == EXIT_FAILURE
        assert "Duplicate Job" in report

    def test_older_attempt_duplicate_failure_is_ignored(self) -> None:
        jobs = [_job(j["name"], "success", attempt=2) for j in _all_good()]
        jobs.append(_job("Duplicate Job", "failure", attempt=1))
        code, _ = evaluate(jobs, run_attempt=2, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_SUCCESS

    def test_run_attempt_filters_stale_failure_from_previous_attempt(self) -> None:
        jobs = [_job(j["name"], "failure", attempt=1) for j in _all_good()]
        jobs.extend(_job(j["name"], "success", attempt=2) for j in _all_good())
        code, _ = evaluate(jobs, run_attempt=2, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_SUCCESS

    def test_current_attempt_missing_gate_is_pending_not_stale_failure(self) -> None:
        jobs = [_job(j["name"], "failure", attempt=1) for j in _all_good()]
        current_attempt = _all_good()[:-1]
        jobs.extend(_job(j["name"], "success", attempt=2) for j in current_attempt)
        code, report = evaluate(jobs, run_attempt=2)
        assert code == EXIT_PENDING
        assert _all_good()[-1]["name"] in report

    def test_runner_route_job_is_strict_and_fails_closed(self) -> None:
        # OMN-18031: the per-run runner routing decision. Registration in BOTH
        # tuples is half the mechanism — routing is deliberately INERT while
        # this repo's trusted seam reads '["ubuntu-latest"]', so deleting the
        # `route` job from ci.yml changes no job's PLACEMENT and would be
        # invisible on a green run without this anchor. Same shape as the
        # companion-merged pin above: FAILURE on red, FAILURE on skip, PENDING
        # on absent — never a vacuous green.
        gate = "Runner Route (OMN-18031) / route"
        assert gate in GATE_JOBS
        assert gate in STRICT_SUCCESS_JOBS
        jobs = [j for j in _all_good() if j["name"] != gate]
        jobs.append(_job(gate, "failure"))
        code, report = evaluate(jobs)
        assert code == EXIT_FAILURE
        assert gate in report
        # A skip must fail closed — the job is unconditional in ci.yml.
        jobs = [j for j in _all_good() if j["name"] != gate]
        jobs.append(_job(gate, "skipped"))
        code, _ = evaluate(jobs)
        assert code == EXIT_FAILURE
        # Absent entirely → PENDING (completeness anchor), never a vacuous green.
        jobs = [j for j in _all_good() if j["name"] != gate]
        code, _ = evaluate(jobs)
        assert code == EXIT_PENDING

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
    def _run(
        self,
        payload: object,
        *extra: str,
        external_runs: list[dict] | None = None,
        event_name: str = "pull_request",
    ) -> subprocess.CompletedProcess[str]:
        # Default to both L4 EXPECTED_EXTERNAL_CONTEXTS green so existing
        # jobs-only scenarios keep their original SUCCESS/FAILURE/PENDING
        # meaning; pass external_runs=[] (or a specific failure fixture)
        # explicitly to exercise the L4 layer itself.
        if external_runs is None:
            external_runs = [
                _check_run(n, "success") for n in EXPECTED_EXTERNAL_CONTEXTS
            ]
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, dir=REPO_ROOT
        ) as handle:
            json.dump(external_runs, handle)
            tmp_path = Path(handle.name)
        try:
            return subprocess.run(
                [
                    sys.executable,
                    "scripts/ci/ci_summary_gate.py",
                    "--jobs-file",
                    "-",
                    "--external-check-runs-file",
                    str(tmp_path),
                    "--event-name",
                    event_name,
                    *extra,
                ],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

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

    def test_cli_run_attempt_ignores_stale_failure(self) -> None:
        jobs = [_job(j["name"], "failure", attempt=1) for j in _all_good()]
        jobs.extend(_job(j["name"], "success", attempt=2) for j in _all_good())
        result = self._run(jobs, "--run-attempt", "2")
        assert result.returncode == EXIT_SUCCESS, result.stdout + result.stderr

    def test_cli_external_check_runs_failure_exit_one(self) -> None:
        bad = [
            _check_run(EXPECTED_EXTERNAL_CONTEXTS[0], "failure"),
            _check_run(EXPECTED_EXTERNAL_CONTEXTS[1], "success"),
        ]
        result = self._run(_all_good(), external_runs=bad)
        assert result.returncode == EXIT_FAILURE, result.stdout + result.stderr

    def test_cli_push_requires_only_producers_that_fire_on_push(self) -> None:
        push_contexts = EXTERNAL_CONTEXTS_BY_EVENT["push"]
        result = self._run(
            _all_good(),
            event_name="push",
            external_runs=[_check_run(name, "success") for name in push_contexts],
        )
        assert result.returncode == EXIT_SUCCESS, result.stdout + result.stderr
        assert "L4 event/context contract: push:" in result.stdout

    def test_cli_pull_request_requires_advisory_context(self) -> None:
        result = self._run(
            _all_good(),
            external_runs=[
                _check_run(name, "success")
                for name in EXTERNAL_CONTEXTS_BY_EVENT["push"]
            ],
        )
        assert result.returncode == EXIT_PENDING, result.stdout + result.stderr

    def test_cli_external_check_runs_empty_is_pending(self) -> None:
        result = self._run(_all_good(), external_runs=[])
        assert result.returncode == EXIT_PENDING, result.stdout + result.stderr

    def test_cli_external_check_runs_flag_omitted_is_pending_not_vacuous_success(
        self,
    ) -> None:
        # A caller that forgets --external-check-runs-file entirely (not just
        # supplies an empty one) must default to PENDING, never a vacuous
        # SUCCESS -- this is the CLI-level guard against the wiring silently
        # regressing back to "L4 never actually enforced."
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ci/ci_summary_gate.py",
                "--jobs-file",
                "-",
                "--event-name",
                "pull_request",
            ],
            input=json.dumps(_all_good()),
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )
        assert result.returncode == EXIT_PENDING, result.stdout + result.stderr

    def test_cli_event_name_is_required_and_unknown_events_fail_closed(self) -> None:
        missing = subprocess.run(
            [sys.executable, "scripts/ci/ci_summary_gate.py", "--jobs-file", "-"],
            input=json.dumps(_all_good()),
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )
        unknown = self._run(_all_good(), event_name="repository_dispatch")
        assert missing.returncode == 2
        assert unknown.returncode == 2


class TestExternalContextEventContracts:
    """L4 contexts apply only to the CI events their producers emit."""

    @pytest.mark.parametrize(
        ("event_name", "expected"),
        [
            ("pull_request", EXPECTED_EXTERNAL_CONTEXTS),
            ("push", EXPECTED_EXTERNAL_CONTEXTS[:1]),
            ("workflow_dispatch", EXPECTED_EXTERNAL_CONTEXTS[:1]),
            ("merge_group", ()),
            ("schedule", ()),
        ],
    )
    def test_event_contracts_are_explicit(
        self, event_name: str, expected: tuple[str, ...]
    ) -> None:
        assert external_contexts_for_event(event_name) == expected

    def test_unknown_event_fails_closed(self) -> None:
        with pytest.raises(ValueError, match="unsupported CI event"):
            external_contexts_for_event("repository_dispatch")

    def test_event_map_matches_live_producer_triggers(self) -> None:
        """An L4 entry applies exactly where its producer can emit it."""

        actual: dict[str, tuple[str, ...]] = {}
        for event_name in EXTERNAL_CONTEXTS_BY_EVENT:
            emitted = []
            for context, filename in EXTERNAL_CONTEXT_PRODUCER_WORKFLOWS.items():
                document = yaml.safe_load((WORKFLOWS_DIR / filename).read_text())
                triggers = {
                    PRODUCER_TRIGGER_ALIASES.get(trigger, trigger)
                    for trigger in _on_block(document)
                }
                if event_name in triggers:
                    emitted.append(context)
            actual[event_name] = tuple(emitted)
        assert actual == EXTERNAL_CONTEXTS_BY_EVENT

    def test_l4_producers_retrigger_when_ci_summary_retriggers_on_pr_edit(self) -> None:
        """A body evidence update must replace a stale L4 preflight verdict."""

        ci_document = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))
        ci_pull_request = _on_block(ci_document)["pull_request"]
        assert isinstance(ci_pull_request, dict)
        assert "edited" in ci_pull_request["types"]

        expected_default_activities = {"opened", "synchronize", "reopened", "edited"}
        for context in ("DB ownership CI twin (B1)",):
            document = yaml.safe_load(
                (
                    WORKFLOWS_DIR / EXTERNAL_CONTEXT_PRODUCER_WORKFLOWS[context]
                ).read_text(encoding="utf-8")
            )
            pull_request = _on_block(document)["pull_request"]
            assert isinstance(pull_request, dict)
            assert expected_default_activities <= set(pull_request["types"])


class TestExpectedExternalContexts:
    """L4 EXPECTED_EXTERNAL_CONTEXTS (enforce-everything gate audit).

    "DB ownership CI twin (B1)" and the advisory-job gate live in separate
    workflow files (check-db-ownership.yml / advisory-job-gate.yml) and are
    therefore invisible to the in-run jobs sweep above; these tests pin
    the resolution against ``commits/{sha}/check-runs`` fixtures directly.
    """

    def test_success_when_both_check_runs_are_green(self) -> None:
        runs = [_check_run(n, "success") for n in EXPECTED_EXTERNAL_CONTEXTS]
        failures, missing = evaluate_external(runs)
        assert failures == []
        assert missing == []

    def test_absent_context_is_missing_not_failure(self) -> None:
        # Every context but one reports green; the one left out must come back
        # PENDING, never a pass. Written over the whole tuple rather than over
        # two hardcoded indices so that registering a new L4 context does not
        # turn this pin red for a reason that has nothing to do with it.
        absent = EXPECTED_EXTERNAL_CONTEXTS[1]
        runs = [
            _check_run(n, "success") for n in EXPECTED_EXTERNAL_CONTEXTS if n != absent
        ]
        failures, missing = evaluate_external(runs)
        assert failures == []
        assert missing == [absent]

    def test_failed_context_is_a_failure(self) -> None:
        runs = [_check_run(n, "success") for n in EXPECTED_EXTERNAL_CONTEXTS]
        runs[0] = _check_run(EXPECTED_EXTERNAL_CONTEXTS[0], "failure")
        failures, missing = evaluate_external(runs)
        assert failures == [EXPECTED_EXTERNAL_CONTEXTS[0]]
        assert missing == []

    def test_skipped_context_is_a_failure_not_a_pass(self) -> None:
        # LOAD-BEARING: unlike GATE_JOBS, L4 external contexts are STRICT
        # success-only. After the always-fire + in-job short-circuit
        # conversion, a GitHub-level 'skipped' on one of these two check-runs
        # would itself be anomalous un-enforcement -- 'skipped' is NOT good
        # here the way it is for GATE_JOBS.
        runs = [_check_run(n, "success") for n in EXPECTED_EXTERNAL_CONTEXTS]
        runs[1] = _check_run(EXPECTED_EXTERNAL_CONTEXTS[1], "skipped")
        failures, _missing = evaluate_external(runs)
        assert failures == [EXPECTED_EXTERNAL_CONTEXTS[1]]

    def test_still_running_context_is_pending_not_failure(self) -> None:
        runs = [_check_run(n, "success") for n in EXPECTED_EXTERNAL_CONTEXTS]
        runs[0] = _check_run(EXPECTED_EXTERNAL_CONTEXTS[0], None, status="in_progress")
        failures, missing = evaluate_external(runs)
        assert failures == []
        assert missing == [EXPECTED_EXTERNAL_CONTEXTS[0]]

    def test_no_external_check_runs_supplied_is_all_missing(self) -> None:
        # Never a vacuous pass: an empty/absent check-runs payload must mark
        # both contexts pending, not silently succeed.
        failures, missing = evaluate_external([])
        assert failures == []
        assert sorted(missing) == sorted(EXPECTED_EXTERNAL_CONTEXTS)

    def test_external_rerun_uses_latest_started_at(self) -> None:
        name = EXPECTED_EXTERNAL_CONTEXTS[0]
        runs = [
            _check_run(name, "failure", started_at="2026-01-01T00:00:00Z"),
            _check_run(name, "success", started_at="2026-01-01T01:00:00Z"),
            *(
                _check_run(n, "success")
                for n in EXPECTED_EXTERNAL_CONTEXTS
                if n != name
            ),
        ]
        failures, missing = evaluate_external(runs)
        assert failures == []
        assert missing == []

    def test_external_stale_newer_attempt_failure_not_hidden_by_older_success(
        self,
    ) -> None:
        name = EXPECTED_EXTERNAL_CONTEXTS[0]
        runs = [
            _check_run(name, "success", started_at="2026-01-01T00:00:00Z"),
            _check_run(name, "failure", started_at="2026-01-01T01:00:00Z"),
            _check_run(EXPECTED_EXTERNAL_CONTEXTS[1], "success"),
        ]
        failures, _missing = evaluate_external(runs)
        assert failures == [name]

    def test_full_evaluate_pending_without_external_check_runs(self) -> None:
        code, report = evaluate(_all_good())
        assert code == EXIT_PENDING
        assert "L4 external contexts missing/pending" in report

    def test_full_evaluate_success_requires_external_contexts_green(self) -> None:
        runs = [_check_run(n, "success") for n in EXPECTED_EXTERNAL_CONTEXTS]
        code, _ = evaluate(_all_good(), external_check_runs=runs)
        assert code == EXIT_SUCCESS

    def test_full_evaluate_failure_when_external_context_red(self) -> None:
        runs = [_check_run(n, "success") for n in EXPECTED_EXTERNAL_CONTEXTS]
        runs[0] = _check_run(EXPECTED_EXTERNAL_CONTEXTS[0], "failure")
        code, report = evaluate(_all_good(), external_check_runs=runs)
        assert code == EXIT_FAILURE
        assert EXPECTED_EXTERNAL_CONTEXTS[0] in report


class TestContractComplianceAdvisory:
    def test_orphan_contract_compliance_remains_advisory(self) -> None:
        # The repo-owned standards reader remains advisory after OCC retirement.
        assert "Contract Compliance" in SOFT_ALLOWLIST
        assert "Contract Compliance" not in GATE_JOBS


# ---------------------------------------------------------------------------
# Fleet-wide completeness-audit classification tables (enforce-everything gate
# audit, omnibase_core priority 7). Every job that can fire on a
# `pull_request` targeting `main`/`dev` in a workflow file OTHER than ci.yml
# (ci.yml's own jobs are covered by the in-run default-deny sweep, opt-out
# only via SOFT_ALLOWLIST -- see the ci_summary_gate.py module docstring) must
# resolve into exactly one of:
#   (a) EXTERNAL_CONTEXT_FILES (L4 EXPECTED_EXTERNAL_CONTEXTS), OR
#   (b) DIRECT_REQUIRED_JOB_CONTEXTS (a literal context name already directly
#       required on `dev`, per the committed branch-protection snapshot), OR
#   (c) EXPLICIT_EXEMPT_JOBS (a one-line reason).
# A job in a NEW workflow file, or a new job in an existing one, satisfies
# none of these and fails test_every_pr_triggered_job_is_classified until a
# human classifies it -- this is the mechanism that keeps "new workflow file
# = structurally invisible" closed for this repo going forward.
# ---------------------------------------------------------------------------


EXTERNAL_CONTEXT_FILES: frozenset[str] = frozenset(
    {
        "check-db-ownership.yml",
        # OMN-18796: the advisory-job gate's caller. Its job resolves to the L4
        # context "advisory-job-gate / advisory-job-gate", so it is classified
        # by EXPECTED_EXTERNAL_CONTEXTS and not by a direct-required row.
        "advisory-job-gate.yml",
    }
)

# (file, job_key) -> literal required-status-check context name(s) that job
# resolves to. Each was verified against the live committed snapshot (see
# fixtures/required_status_checks_snapshot.json) at audit time, not guessed;
# test_direct_required_job_contexts_are_all_still_live re-checks every one.
DIRECT_REQUIRED_JOB_CONTEXTS: dict[tuple[str, str], tuple[str, ...]] = {
    ("contract-validation.yml", "contract-validation"): ("contract-validation",),
    ("dep-provenance-gate.yml", "dep-provenance-gate"): ("Dep Provenance Gate",),
    ("deploy-gate.yml", "deploy-gate"): ("deploy-gate / deploy-gate",),
    ("main-target-guard.yml", "main-target-guard"): ("main-target-guard",),
    ("no-faked-boundary.yml", "no-faked-boundary-gate"): ("No Faked Boundary Gate",),
    ("omni-standards-compliance.yml", "onex-compliance"): (
        "ONEX Architecture Compliance",
    ),
    ("omni-standards-compliance.yml", "legacy-compatibility-check"): (
        "Legacy Compatibility Check",
    ),
    ("omni-standards-compliance.yml", "ecosystem-validation"): (
        "Ecosystem Integration Validation",
    ),
    ("omni-standards-compliance.yml", "forbidden-pattern-scan"): (
        "Decommissioned Pattern Scanner (OMN-4801)",
    ),
    ("omni-standards-compliance.yml", "ci-naming-convention"): (
        "CI Naming Convention",
    ),
    ("pr-title-check-caller.yml", "pr-title"): ("pr-title / check-title",),
    ("precommit-parity-gate.yml", "precommit-parity-gate"): ("Precommit Parity Gate",),
    ("product-readiness-shadow.yml", "lint-shadow"): ("lint (shadow)",),
    ("product-readiness-shadow.yml", "typecheck-shadow"): ("typecheck (shadow)",),
    ("product-readiness-shadow.yml", "tests-shadow"): ("tests+coverage (shadow)",),
    ("product-readiness-shadow.yml", "product-readiness"): (
        "product-readiness / evaluate",
    ),
    ("product-readiness-shadow.yml", "reason-graph"): ("reason-graph",),
    ("receipt-honesty.yml", "receipt-honesty"): ("receipt-honesty",),
    ("required-check-skip-guard-caller.yml", "required-check-skip-guard"): (
        "required-check-skip-guard / check-skip-vectors",
    ),
    ("security-scan.yml", "codeql"): ("CodeQL", "CodeQL / CodeQL Analysis (python)"),
    ("semantic-diff-labeler.yml", "label"): ("AST Risk Labeler",),
    ("stale-todo-gate.yml", "stale-todo-gate"): ("Stale TODO Gate",),
    ("url-authority-gate.yml", "url-authority-gate"): ("URL Authority Gate",),
    ("validator-fsm-handler-drift.yml", "fsm-handler-drift"): ("fsm-handler-drift",),
    ("validator-no-plugin-daemon-classes.yml", "no-plugin-daemon-classes"): (
        "no-plugin-daemon-classes",
    ),
    ("validator-runtime-profiles.yml", "runtime-profiles"): ("runtime-profiles",),
    ("check-handshake.yml", "check-handshake"): ("Check architecture handshake",),
    ("canonical-inference-gate.yml", "canonical-inference-gate"): (
        "Canonical Inference Gate",
    ),
    ("call-reject-skip.yml", "call-reject-skip-token"): (
        "call-reject-skip-token / scan / reject-skip-gate-token",
    ),
}

EXPLICIT_EXEMPT_JOBS: dict[tuple[str, str], str] = {
    ("auto-merge.yml", "pre-check"): (
        "auto-merge enablement helper (Resolve PR fanout guard), not a PR "
        "content validator; GitHub's native auto-merge still waits on every "
        "required status check before it will actually merge."
    ),
    ("auto-merge.yml", "auto-merge"): (
        "enables GitHub's native auto-merge on approval/ready-for-review "
        "events; does not itself validate PR content and does not bypass "
        "required status checks."
    ),
    ("auto-tag-on-merge.yml", "auto-tag"): (
        "triggers only on pull_request closed -- post-merge tag automation, "
        "structurally cannot gate the merge it fires after."
    ),
    ("propagate-config.yml", "propagate"): (
        "config-propagation automation scoped via on.pull_request.paths to "
        "its own script/config files -- there is nothing to propagate-dry-run "
        "when those paths are untouched, unlike a drift check meaningful on "
        "every PR; not flagged as a required validator by this audit."
    ),
    ("todo-audit-on-merge.yml", "todo-audit"): (
        "triggers only on pull_request closed -- post-merge TODO/ticket "
        "audit, structurally cannot be a merge gate (same class as "
        "auto-tag-on-merge)."
    ),
}


def _on_block(doc: dict) -> dict:
    """Return the ``on:`` trigger block.

    PyYAML's default (YAML 1.1) resolver parses the bare scalar key ``on`` as
    the boolean ``True`` -- ``doc["on"]`` is absent; the real trigger block is
    at ``doc[True]``. Handle both so this helper is safe regardless.
    """

    on = doc.get("on", doc.get(True, {}))
    if isinstance(on, list):
        return dict.fromkeys(on)
    if isinstance(on, str):
        return {on: None}
    if isinstance(on, dict):
        return on
    return {}


def _pr_targets_main_or_dev(on: dict) -> bool:
    if "pull_request" not in on:
        return False
    pr = on["pull_request"]
    if not isinstance(pr, dict):
        return True  # bare `pull_request:` (no filters) applies to all branches
    branches = pr.get("branches")
    if branches is None:
        return True
    return any(b in ("main", "dev") for b in branches)


def _pr_triggered_jobs(path: Path) -> dict[str, dict]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    on = _on_block(doc)
    if not _pr_targets_main_or_dev(on):
        return {}
    return doc.get("jobs", {}) or {}


def _required_snapshot_contexts() -> set[str]:
    data = json.loads(
        (FIXTURES_DIR / "required_status_checks_snapshot.json").read_text(
            encoding="utf-8"
        )
    )
    return set(data["contexts"])


class TestEnforceEverythingCompleteness:
    """Fleet-wide completeness audit pin (enforce-everything gate, OMN-14127).

    Enumerates every PR-triggered job across .github/workflows/*.yml (other
    than ci.yml, whose own jobs are already covered by the in-run
    default-deny sweep) and asserts each resolves to a classified bucket. A
    newly added job that resolves to none of them fails
    ``test_every_pr_triggered_job_is_classified`` until a human classifies
    it -- this is what mechanically keeps "new workflow file = structurally
    invisible" closed for this repo, rather than relying on someone
    remembering to update this file.
    """

    def test_check_db_ownership_and_llm_refs_drift_have_no_paths_filter(self) -> None:
        # Pins the always-fire + in-job short-circuit conversion: an asserted
        # L4 context must never be silently absent because touched paths
        # didn't match an on.pull_request.paths filter.
        for filename in EXTERNAL_CONTEXT_FILES:
            doc = yaml.safe_load((WORKFLOWS_DIR / filename).read_text(encoding="utf-8"))
            on = _on_block(doc)
            for trigger in ("push", "pull_request"):
                block = on.get(trigger)
                if isinstance(block, dict):
                    assert "paths" not in block, (
                        f"{filename} {trigger}: still has a paths filter -- an "
                        "asserted L4 context must always fire"
                    )

    def test_every_pr_triggered_job_is_classified(self) -> None:
        required_snapshot = _required_snapshot_contexts()
        unclassified: list[str] = []
        for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
            if path.name == "ci.yml":
                continue
            jobs = _pr_triggered_jobs(path)
            for job_key, job in jobs.items():
                if path.name in EXTERNAL_CONTEXT_FILES:
                    continue  # L4 EXPECTED_EXTERNAL_CONTEXTS
                key = (path.name, job_key)
                if key in DIRECT_REQUIRED_JOB_CONTEXTS:
                    contexts = DIRECT_REQUIRED_JOB_CONTEXTS[key]
                    missing = [c for c in contexts if c not in required_snapshot]
                    if missing:
                        unclassified.append(
                            f"{path.name}::{job_key} claims direct-required "
                            f"context(s) {missing} not present in the snapshot"
                        )
                    continue
                if key in EXPLICIT_EXEMPT_JOBS:
                    continue
                unclassified.append(f"{path.name}::{job_key}")
        assert not unclassified, (
            "PR-triggered job(s) not classified into EXPECTED_EXTERNAL_CONTEXTS, "
            "DIRECT_REQUIRED_JOB_CONTEXTS, or EXPLICIT_EXEMPT_JOBS -- classify "
            f"each in tests/unit/scripts/ci/test_ci_summary_gate.py: {unclassified}"
        )

    def test_direct_required_job_contexts_are_all_still_live(self) -> None:
        # Falsification control: every literal context name this test relies
        # on must actually be present in the committed snapshot, so a typo or
        # a stale/renamed entry cannot silently pass by never being checked.
        required_snapshot = _required_snapshot_contexts()
        all_named = {
            c for names in DIRECT_REQUIRED_JOB_CONTEXTS.values() for c in names
        }
        missing = sorted(all_named - required_snapshot)
        assert not missing, (
            f"contexts referenced but absent from the snapshot: {missing}"
        )

    def test_product_readiness_shadow_header_matches_live_snapshot(self) -> None:
        # Pins the header-comment fix (product-readiness-shadow.yml): every
        # context the corrected header claims is live-required must actually
        # be present in the snapshot.
        required_snapshot = _required_snapshot_contexts()
        for context in (
            "lint (shadow)",
            "typecheck (shadow)",
            "tests+coverage (shadow)",
            "reason-graph",
            "product-readiness / evaluate",
        ):
            assert context in required_snapshot, (
                f"{context} expected live-required per the corrected "
                "product-readiness-shadow.yml header comment"
            )

    def test_retired_validators_are_workflow_dispatch_only_or_directly_required(
        self,
    ) -> None:
        # Pins the OMN-14877/OMN-14430 migration: a validator-*.yml file is
        # either (a) retired to workflow_dispatch-only (its live twin is an
        # unconditional ci.yml job, already covered by the default-deny
        # sweep), or (b) still a live PR-triggered validator, in which case it
        # MUST be directly required -- otherwise a future silent removal from
        # branch protection would leave it enforcing nothing.
        required_snapshot = _required_snapshot_contexts()
        for path in sorted(WORKFLOWS_DIR.glob("validator-*.yml")):
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            on = _on_block(doc)
            if _pr_targets_main_or_dev(on):
                for job_key, job in (doc.get("jobs", {}) or {}).items():
                    name = job.get("name", job_key)
                    assert name in required_snapshot, (
                        f"{path.name}::{job_key} ('{name}') fires on pull_request "
                        "but is not directly required -- either restore its "
                        "required-status-check or convert it back to "
                        "workflow_dispatch-only"
                    )
            else:
                assert set(on.keys()) == {"workflow_dispatch"}, (
                    f"{path.name} is neither a live PR validator nor "
                    "workflow_dispatch-only -- classify it"
                )


# --------------------------------------------------------------------------- #
# OMN-18062 -- a `skipped` row that lands on a head SHA which ALREADY carries a
# non-skipped row for the same context name is a RE-TRIGGER ARTIFACT, not a
# verdict about that head.
#
# Live shape being pinned (onex_change_control#8709, 2026-09-08): `gh pr edit`
# fired a second `pull_request` run of a workflow whose `types:` include
# `edited`; a job whose own `if:` excludes `edited` was SKIPPED, and GitHub
# wrote a fresh `skipped` check-run onto the unchanged head 64 seconds after
# that same job reported `success`. Latest-wins resolution
# (`_external_check_states`) read the newest row; L4 admits only `success`; the
# required `CI Summary` context failed closed on a head nothing regressed on.
# Re-running `CI Summary` could not clear it -- the skip is and stays the
# newest row -- so only a new head SHA could.
#
# This was fixed in four repos (omnimarket#2422, onex_change_control#8748,
# omnibase_infra#3348, omniclaude#2126) and NOT here; the defect was
# reproduced against this file's own pre-fix code before this suite was added.
#
# Every relaxation below is paired with a positive control that must STILL
# fail, and the head-SHA partition is pinned separately.
# --------------------------------------------------------------------------- #

_HEAD_A = "a" * 40
_HEAD_B = "b" * 40
_T0 = "2026-09-08T20:47:00Z"
_T0_PLUS_64 = "2026-09-08T20:48:04Z"


def _external_rows(*, head_sha: str = _HEAD_A, started_at: str = _T0) -> list[dict]:
    """Every L4 context present + completed + success on one head."""

    return [
        _check_run(name, "success", started_at=started_at, head_sha=head_sha)
        for name in EXPECTED_EXTERNAL_CONTEXTS
    ]


def _with_second_row(
    target: str,
    conclusion: str | None,
    *,
    status: str = "completed",
    head_sha: str = _HEAD_A,
) -> list[dict]:
    """All-green L4 rows, plus a SECOND row for ``target`` 64 seconds later."""

    runs = _external_rows()
    runs.append(
        _check_run(
            target,
            conclusion,
            status=status,
            started_at=_T0_PLUS_64,
            head_sha=head_sha,
        )
    )
    return runs


class TestSupersededSkips:
    """OMN-18062 port: a re-trigger skip must not supersede a real verdict."""

    def test_all_green_baseline_is_success(self) -> None:
        """CONTROL for every zero below: the unperturbed fixture passes."""

        failures, missing = evaluate_external(_external_rows())
        assert failures == []
        assert missing == []

    def test_skip_after_success_on_same_head_is_not_a_regression(self) -> None:
        """GREEN: success at t0, skipped at t0+64s, SAME head -> success.

        This is the case that was failing closed before this change.
        """

        target = EXPECTED_EXTERNAL_CONTEXTS[0]
        runs = _with_second_row(target, "skipped")
        failures, missing = evaluate_external(runs)
        assert failures == [], failures
        assert missing == [], missing

    def test_failure_after_success_on_same_head_still_fails(self) -> None:
        """POSITIVE CONTROL: a real verdict at t0+64s still wins on recency."""

        target = EXPECTED_EXTERNAL_CONTEXTS[0]
        failures, _missing = evaluate_external(_with_second_row(target, "failure"))
        assert failures == [target]

    def test_cancelled_after_success_on_same_head_still_fails(self) -> None:
        """POSITIVE CONTROL: `cancelled` is a verdict too, not an artifact."""

        target = EXPECTED_EXTERNAL_CONTEXTS[0]
        failures, _missing = evaluate_external(_with_second_row(target, "cancelled"))
        assert failures == [target]

    def test_lone_skip_with_no_other_row_still_fails_closed(self) -> None:
        """POSITIVE CONTROL: a name whose ONLY row is `skipped` fails closed.

        This is the skip-as-pass vector (OMN-15057 / OMN-14854) the strict L4
        bar exists for -- a producer whose `if:` was false for the whole life
        of the head never ran, and must never read green.
        """

        target = EXPECTED_EXTERNAL_CONTEXTS[0]
        runs = [r for r in _external_rows() if r["name"] != target]
        runs.append(
            _check_run(target, "skipped", started_at=_T0_PLUS_64, head_sha=_HEAD_A)
        )
        failures, _missing = evaluate_external(runs)
        assert failures == [target]

    def test_in_progress_after_success_is_still_pending(self) -> None:
        """POSITIVE CONTROL: a live re-run stays PENDING, never stale-green."""

        target = EXPECTED_EXTERNAL_CONTEXTS[0]
        runs = _with_second_row(target, None, status="in_progress")
        failures, missing = evaluate_external(runs)
        assert failures == []
        assert missing == [target]

    def test_skip_after_success_does_not_leak_across_names(self) -> None:
        """POSITIVE CONTROL: a non-skipped row for one name cannot clear a
        skip recorded against a DIFFERENT name."""

        rows = [
            _check_run("a", "success", head_sha=_HEAD_A),
            _check_run("b", "skipped", head_sha=_HEAD_A),
        ]
        assert drop_superseded_skips(rows) == rows

    def test_skip_on_a_different_head_is_not_superseded(self) -> None:
        """The head SHA partitions supersession (OMN-18062 follow-up).

        A `success` recorded on head A is a verdict about head A. It must not
        clear a `skipped` recorded on head B -- doing so would re-open the
        skip-as-pass vector on the head actually being gated. Unreachable
        through the sanctioned caller (which fetches one head's
        `commits/{sha}/check-runs`), so this makes it a property of the
        function rather than of the convention.
        """

        target = EXPECTED_EXTERNAL_CONTEXTS[0]
        runs = _with_second_row(target, "skipped", head_sha=_HEAD_B)
        assert len(drop_superseded_skips(runs)) == len(runs)
        failures, _missing = evaluate_external(runs)
        assert failures == [target]

    def test_rows_without_a_head_sha_still_supersede(self) -> None:
        """POSITIVE CONTROL for the partition: rows carrying no `head_sha`
        share one partition, so a payload without head SHAs behaves exactly as
        it did before the head guard."""

        rows = [
            {"name": "x", "status": "completed", "conclusion": "success"},
            {"name": "x", "status": "completed", "conclusion": "skipped"},
        ]
        kept = drop_superseded_skips(rows)
        assert [r["conclusion"] for r in kept] == ["success"]


class TestSuiteRerunInFlightOmn20427:
    """A stale non-success L4 row whose own check suite is re-running is PENDING.

    Replays omnibase_core#1873 (check suite 100653109843): attempt 1 of
    check-db-ownership.yml left ``DB ownership CI twin (B1)`` skipped at
    23:06:32Z; the whole-run rerun's ``occ-preflight / eligibility`` was in
    progress from 23:46:47Z when ``CI Summary`` polled at 23:47:03Z.
    """

    NOW = datetime(2026, 10, 3, 23, 47, 3, tzinfo=UTC)
    SUITE = {"id": 100653109843}

    def _runs(self, sibling_status: str, sibling_started: str) -> list[dict]:
        db = EXPECTED_EXTERNAL_CONTEXTS[0]
        runs = [_check_run(n, "success") for n in EXPECTED_EXTERNAL_CONTEXTS if n != db]
        stale = _check_run(db, "skipped", started_at="2026-10-03T23:06:33Z")
        stale["completed_at"] = "2026-10-03T23:06:32Z"
        stale["check_suite"] = self.SUITE
        sibling = _check_run(
            "occ-preflight / eligibility",
            None if sibling_status != "completed" else "success",
            status=sibling_status,
            started_at=sibling_started,
        )
        sibling["check_suite"] = self.SUITE
        return [*runs, stale, sibling]

    def test_stale_skip_is_pending_while_its_suite_reruns(self) -> None:
        runs = self._runs("in_progress", "2026-10-03T23:46:47Z")
        failures, missing = evaluate_external(runs, now=self.NOW)
        assert failures == []
        assert missing == [EXPECTED_EXTERNAL_CONTEXTS[0]]
        assert provisional_external_verdicts(runs, now=self.NOW) == [
            EXPECTED_EXTERNAL_CONTEXTS[0]
        ]

    def test_stale_skip_fails_once_the_suite_has_settled(self) -> None:
        runs = self._runs("completed", "2026-10-03T23:46:47Z")
        failures, _missing = evaluate_external(runs, now=self.NOW)
        assert failures == [EXPECTED_EXTERNAL_CONTEXTS[0]]

    def test_running_sibling_older_than_the_stale_row_does_not_hold(self) -> None:
        runs = self._runs("in_progress", "2026-10-03T23:00:00Z")
        failures, _missing = evaluate_external(runs, now=self.NOW)
        assert failures == [EXPECTED_EXTERNAL_CONTEXTS[0]]

    def test_running_row_in_another_suite_does_not_hold(self) -> None:
        runs = self._runs("in_progress", "2026-10-03T23:46:47Z")
        runs[-1]["check_suite"] = {"id": 1}
        failures, _missing = evaluate_external(runs, now=self.NOW)
        assert failures == [EXPECTED_EXTERNAL_CONTEXTS[0]]


class TestExternalDefaultDenySweep:
    """OMN-17427: an unregistered external verdict must reach CI Summary."""

    NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)

    def test_red_unregistered_context_fails_and_green_passes(self) -> None:
        for conclusion, expected in [
            ("failure", EXIT_FAILURE),
            ("success", EXIT_SUCCESS),
        ]:
            code, report = evaluate(
                _all_good(),
                external_check_runs=[
                    *_ALL_EXTERNAL_GREEN,
                    _check_run("Unregistered Gate", conclusion),
                ],
                now=self.NOW,
            )
            assert code == expected, report
            assert (
                "external default-deny sweep: 1 unregistered context(s) judged"
                in report
            )
            if conclusion == "failure":
                assert "Unregistered Gate (failure)" in report

    @pytest.mark.parametrize(
        "conclusion",
        [
            "skipped",
            "neutral",
            "cancelled",
            "failure",
            "timed_out",
            "action_required",
            "startup_failure",
            "stale",
            None,
        ],
    )
    def test_only_success_passes(self, conclusion: str | None) -> None:
        assert frozenset({"success"}) == gate.SWEEP_GOOD_CONCLUSIONS
        code, report = evaluate(
            _all_good(),
            external_check_runs=[
                *_ALL_EXTERNAL_GREEN,
                _check_run("Unregistered Gate", conclusion),
            ],
            now=self.NOW,
        )
        assert code == EXIT_FAILURE, report
        reason = (
            "cancelled_without_replacement"
            if conclusion == "cancelled"
            else str(conclusion)
        )
        assert f"Unregistered Gate ({reason}" in report

    @pytest.mark.parametrize("status", ["queued", "in_progress", "waiting"])
    def test_running_rows_hold_pending_until_success(self, status: str) -> None:
        row = _check_run("Unregistered Gate", None, status=status)
        code, report = evaluate(
            _all_good(), external_check_runs=[*_ALL_EXTERNAL_GREEN, row], now=self.NOW
        )
        assert code == EXIT_PENDING, report
        assert (
            "external sweep rows still running (PENDING, re-polled): Unregistered Gate"
            in report
        )
        row.update(status="completed", conclusion="success")
        assert (
            evaluate(
                _all_good(),
                external_check_runs=[*_ALL_EXTERNAL_GREEN, row],
                now=self.NOW,
            )[0]
            == EXIT_SUCCESS
        )

    @pytest.mark.parametrize(
        ("conclusion", "expected"),
        [("success", EXIT_SUCCESS), ("failure", EXIT_FAILURE)],
    )
    def test_ghost_rows_reuse_core_normalization(
        self, conclusion: str, expected: int
    ) -> None:
        row = _check_run(
            "Unregistered Gate",
            conclusion,
            status="in_progress",
            completed_at="2026-10-16T12:00:00Z",
        )
        code, report = evaluate(
            _all_good(), external_check_runs=[*_ALL_EXTERNAL_GREEN, row], now=self.NOW
        )
        assert code == expected, report
        assert "external sweep rows still running" not in report
        row.pop("completed_at")
        assert (
            evaluate(
                _all_good(),
                external_check_runs=[*_ALL_EXTERNAL_GREEN, row],
                now=self.NOW,
            )[0]
            == EXIT_PENDING
        )

    @pytest.mark.parametrize("conclusion", ["skipped", "cancelled", "failure"])
    def test_provisional_grace_is_pending_then_fails_and_requires_a_clock(
        self, conclusion: str
    ) -> None:
        row = _check_run(
            "Unregistered Gate", conclusion, completed_at="2026-10-17T11:59:30Z"
        )
        rows = [*_ALL_EXTERNAL_GREEN, row]
        code, report = evaluate(_all_good(), external_check_runs=rows, now=self.NOW)
        assert code == EXIT_PENDING, report
        assert "external sweep rows awaiting an automatic replacement" in report
        for observation in [None, self.NOW + timedelta(days=1)]:
            code, report = evaluate(
                _all_good(), external_check_runs=rows, now=observation
            )
            assert code == EXIT_FAILURE, report
            if conclusion == "cancelled":
                assert "cancelled_without_replacement" in report
                assert "re-run" in report

    def test_existing_skip_supersession_and_latest_wins_are_preserved(self) -> None:
        original = _check_run(
            "Unregistered Gate", "success", head_sha=_HEAD_A, started_at=_T0
        )
        for conclusion, expected in [
            ("skipped", EXIT_SUCCESS),
            ("failure", EXIT_FAILURE),
            ("cancelled", EXIT_FAILURE),
            (None, EXIT_PENDING),
        ]:
            replacement = _check_run(
                "Unregistered Gate",
                conclusion,
                status="in_progress" if conclusion is None else "completed",
                head_sha=_HEAD_A,
                started_at=_T0_PLUS_64,
            )
            code, report = evaluate(
                _all_good(),
                external_check_runs=[*_ALL_EXTERNAL_GREEN, original, replacement],
                now=self.NOW,
            )
            assert code == expected, report
        # Same-second rows retain core's check-run id tie-break.
        original["id"] = 2
        replacement = {**original, "id": 1, "conclusion": "failure"}
        assert (
            evaluate(
                _all_good(),
                external_check_runs=[*_ALL_EXTERNAL_GREEN, original, replacement],
                now=self.NOW,
            )[0]
            == EXIT_SUCCESS
        )
        replacement["id"] = 3
        assert (
            evaluate(
                _all_good(),
                external_check_runs=[*_ALL_EXTERNAL_GREEN, original, replacement],
                now=self.NOW,
            )[0]
            == EXIT_FAILURE
        )

    def test_accounted_names_are_not_double_judged(self) -> None:
        rows = [
            *_ALL_EXTERNAL_GREEN,
            *[_check_run(name, "skipped") for name in GATE_JOBS],
            _check_run("CI Summary", None, status="in_progress"),
        ]
        rows += [_check_run(name, "failure") for name in SOFT_ALLOWLIST]
        code, report = evaluate(_all_good(), external_check_runs=rows, now=self.NOW)
        assert code == EXIT_SUCCESS, report
        assert "external default-deny sweep: 0 unregistered context(s) judged" in report
        rows.append(_check_run("Unregistered Gate", "failure"))
        assert (
            evaluate(_all_good(), external_check_runs=rows, now=self.NOW)[0]
            == EXIT_FAILURE
        )

    def test_active_contexts_are_accounted_but_inactive_names_are_swept(self) -> None:
        name = EXPECTED_EXTERNAL_CONTEXTS[0]
        rows = [_check_run(name, "skipped")]
        code, report = evaluate(
            _all_good(), external_check_runs=rows, external_contexts=(), now=self.NOW
        )
        assert code == EXIT_FAILURE, report
        assert f"{name} (skipped)" in report
        code, report = evaluate(
            _all_good(),
            external_check_runs=[_check_run(name, "success")],
            external_contexts=(name,),
            now=self.NOW,
        )
        assert code == EXIT_SUCCESS, report
        assert "external default-deny sweep: 0 unregistered context(s) judged" in report

    def test_own_run_rows_not_yet_in_jobs_are_not_external(self) -> None:
        jobs = [{**row, "run_id": 7} for row in _all_good()]
        row = {
            **_check_run("Late own job", "skipped"),
            "details_url": "https://github.com/OmniNode-ai/omnibase_core/actions/runs/7/job/9",
        }
        code, report = evaluate(
            jobs, external_check_runs=[*_ALL_EXTERNAL_GREEN, row], now=self.NOW
        )
        assert code == EXIT_SUCCESS, report
        row["details_url"] = row["details_url"].replace("runs/7/", "runs/8/")
        assert (
            evaluate(
                jobs, external_check_runs=[*_ALL_EXTERNAL_GREEN, row], now=self.NOW
            )[0]
            == EXIT_FAILURE
        )

    @pytest.mark.parametrize("event", sorted(gate.SWEEP_NON_PR_EVENTS))
    def test_known_non_pr_events_are_exempt_with_pr_positive_control(
        self, event: str
    ) -> None:
        row = {
            **_check_run("Unregistered Gate", "failure"),
            "details_url": "https://github.com/OmniNode-ai/omnibase_core/actions/runs/777/job/9",
        }
        for observed, expected in [
            (event, EXIT_SUCCESS),
            ("pull_request", EXIT_FAILURE),
        ]:
            code, report = evaluate(
                _all_good(),
                external_check_runs=[*_ALL_EXTERNAL_GREEN, row],
                workflow_runs=[{"id": 777, "event": observed}],
                now=self.NOW,
            )
            assert code == expected, report

    @pytest.mark.parametrize(
        "event", ["pull_request", "pull_request_target", "dynamic", "new_event"]
    )
    def test_deny_list_polarity_sweeps_other_events(self, event: str) -> None:
        row = {
            **_check_run("Unregistered Gate", "failure"),
            "details_url": "https://github.com/OmniNode-ai/omnibase_core/actions/runs/777/job/9",
        }
        code, report = evaluate(
            _all_good(),
            external_check_runs=[*_ALL_EXTERNAL_GREEN, row],
            workflow_runs=[{"id": 777, "event": event}],
            now=self.NOW,
        )
        assert code == EXIT_FAILURE, report

    @pytest.mark.parametrize("provenance", ["app", "absent", "bad_url", "no_index"])
    def test_unresolved_events_are_swept(self, provenance: str) -> None:
        row = _check_run("Unregistered Gate", "failure")
        runs = [{"id": 777, "event": "schedule"}]
        if provenance != "app":
            row["details_url"] = (
                "unparseable"
                if provenance == "bad_url"
                else "https://github.com/OmniNode-ai/omnibase_core/actions/runs/888/job/9"
            )
        code, report = evaluate(
            _all_good(),
            external_check_runs=[*_ALL_EXTERNAL_GREEN, row],
            workflow_runs=None if provenance == "no_index" else runs,
            now=self.NOW,
        )
        assert code == EXIT_FAILURE, report
        assert "Unregistered Gate (failure)" in report

    def test_event_resolution_reads_urls_and_suite_and_rejects_bad_ids(self) -> None:
        events = gate.check_run_event_index(
            [
                {"id": "42", "event": "push"},
                {"id": 0, "event": "push"},
                {"id": "bad", "event": "push"},
                {"id": 43},
            ]
        )
        assert events == {42: "push"}
        url = "https://github.com/OmniNode-ai/omnibase_core/actions/runs/42/job/9"
        for row in [
            {"html_url": url},
            {"details_url": url},
            {"check_suite": {"workflow_run": {"id": 42}}},
            {"check_suite": {"workflow_run_id": 42}},
        ]:
            assert gate.check_run_workflow_run_id(row) == 42
            assert gate.resolve_check_run_event(row, events) == "push"
        for row in [
            {},
            {"details_url": "unreadable"},
            {"check_suite": {"workflow_run_id": "bad"}},
        ]:
            assert gate.resolve_check_run_event(row, events) is None
        assert gate.check_run_event_index(None) == {}

    def test_non_pr_row_cannot_hide_a_pr_verdict_with_the_same_name(self) -> None:
        pr = {
            **_check_run("Shared Gate", "failure", started_at=_T0),
            "details_url": "https://github.com/OmniNode-ai/omnibase_core/actions/runs/7/job/9",
        }
        push = {
            **_check_run("Shared Gate", "success", started_at=_T0_PLUS_64),
            "details_url": "https://github.com/OmniNode-ai/omnibase_core/actions/runs/8/job/9",
        }
        code, report = evaluate(
            _all_good(),
            external_check_runs=[*_ALL_EXTERNAL_GREEN, pr, push],
            workflow_runs=[
                {"id": 7, "event": "pull_request"},
                {"id": 8, "event": "push"},
            ],
            now=self.NOW,
        )
        assert code == EXIT_FAILURE, report
        assert "Shared Gate (failure)" in report

    def test_same_suite_rerun_holds_stale_verdict_until_settled(self) -> None:
        row = {
            **_check_run(
                "Unregistered Gate", "skipped", completed_at="2026-10-16T12:00:00Z"
            ),
            "check_suite": {"id": 1},
        }
        sibling = {
            **_check_run(
                sorted(SOFT_ALLOWLIST)[0],
                None,
                status="in_progress",
                started_at="2026-10-17T11:59:30Z",
            ),
            "check_suite": {"id": 1},
        }
        rows = [*_ALL_EXTERNAL_GREEN, row, sibling]
        code, report = evaluate(_all_good(), external_check_runs=rows, now=self.NOW)
        assert code == EXIT_PENDING, report
        sibling.update(status="completed", conclusion="success")
        assert (
            evaluate(_all_good(), external_check_runs=rows, now=self.NOW)[0]
            == EXIT_FAILURE
        )

    def test_newer_producer_run_holds_stale_verdict_until_settled(self) -> None:
        row = {
            **_check_run(
                "Unregistered Gate",
                "cancelled",
                completed_at="2026-10-16T12:00:00Z",
                head_sha=_HEAD_A,
            ),
            "details_url": "https://github.com/OmniNode-ai/omnibase_core/actions/runs/7/job/9",
        }
        runs = [
            {
                "id": run_id,
                "workflow_id": 42,
                "event": "pull_request",
                "head_sha": _HEAD_A,
                "status": status,
            }
            for run_id, status in [(7, "completed"), (8, "in_progress")]
        ]
        rows = [*_ALL_EXTERNAL_GREEN, row]
        code, report = evaluate(
            _all_good(), external_check_runs=rows, workflow_runs=runs, now=self.NOW
        )
        assert code == EXIT_PENDING, report
        runs[1]["status"] = "completed"
        assert (
            evaluate(
                _all_good(), external_check_runs=rows, workflow_runs=runs, now=self.NOW
            )[0]
            == EXIT_FAILURE
        )

    def test_failure_takes_precedence_over_pending(self) -> None:
        rows = [
            *_ALL_EXTERNAL_GREEN,
            _check_run("Running Gate", None, status="in_progress"),
            _check_run("Red Gate", "failure"),
        ]
        code, report = evaluate(_all_good(), external_check_runs=rows, now=self.NOW)
        assert code == EXIT_FAILURE, report
        assert "Red Gate (failure)" in report
        assert (
            "external sweep rows still running (PENDING, re-polled): Running Gate"
            in report
        )


# The check-run name GitHub posts for propagate-config.yml's skipped job on a
# path-matched pull request (omnibase_core#2047, run 39119407826).
PROPAGATE_PLACEHOLDER = (
    "Propagate ${{ (inputs.propagation_name || 'release-triggered') }}"
)


class TestExternalSweepExclusions:
    """OMN-17427: every tolerance is bounded, validated and visible."""

    NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)
    ENTRY = gate.SweepExclusion(
        "Owned exception", "OMN-17427", "2026-10-17", "2026-12-20"
    )

    def test_registry_contains_exactly_the_measured_valid_unexpired_entries(
        self,
    ) -> None:
        assert set(gate.EXTERNAL_SWEEP_EXCLUSIONS) == {
            "handshake-policy-gate",
            "Enable Auto-Merge",
            PROPAGATE_PLACEHOLDER,
        }
        assert gate.validate_sweep_exclusions(gate.EXTERNAL_SWEEP_EXCLUSIONS) == []
        active, expired = gate.active_sweep_exclusions(
            gate.EXTERNAL_SWEEP_EXCLUSIONS, now=self.NOW
        )
        assert active == frozenset(gate.EXTERNAL_SWEEP_EXCLUSIONS)
        assert expired == ()
        assert not active.intersection(EXPECTED_EXTERNAL_CONTEXTS)
        for entry in gate.EXTERNAL_SWEEP_EXCLUSIONS.values():
            assert entry.reason.strip()
            assert entry.ticket == "OMN-17427"
            assert entry.added in {"2026-10-17", "2026-10-18"}
            assert entry.expires == "2026-12-20"
        with pytest.raises(FrozenInstanceError):
            self.ENTRY.reason = "changed"

    @pytest.mark.parametrize(
        "name", ["handshake-policy-gate", "Enable Auto-Merge", PROPAGATE_PLACEHOLDER]
    )
    def test_shipped_exclusions_admit_skips_but_not_unregistered_reds(
        self, name: str
    ) -> None:
        rows = [*_ALL_EXTERNAL_GREEN, _check_run(name, "skipped")]
        code, report = evaluate(_all_good(), external_check_runs=rows, now=self.NOW)
        assert code == EXIT_SUCCESS, report
        assert f"exclusions applied: {name}" in report
        rows.append(_check_run("Unregistered Gate", "failure"))
        code, report = evaluate(_all_good(), external_check_runs=rows, now=self.NOW)
        assert code == EXIT_FAILURE, report
        assert "Unregistered Gate (failure)" in report

    @pytest.mark.parametrize(
        ("fields", "fragment"),
        [
            ({"reason": "  "}, "reason is empty"),
            ({"ticket": "no ticket"}, "is not an OMN-<number> reference"),
            ({"ticket": "OMN-17427junk"}, "is not an OMN-<number> reference"),
            ({"added": "soon"}, "added 'soon'"),
            ({"added": "2026-02-30"}, "added '2026-02-30'"),
            ({"expires": ""}, "expires ''"),
            ({"expires": "2026-13-20"}, "expires '2026-13-20'"),
            ({"expires": "2026-10-17"}, "is not after added"),
            ({"expires": "2026-10-16"}, "is not after added"),
            ({"expires": "2027-10-17"}, "exceeds the 90d cap"),
            ({"reason": None}, "reason is empty"),
            ({"ticket": None}, "is not an OMN-<number> reference"),
            ({"added": None}, "not a YYYY-MM-DD date"),
        ],
    )
    def test_malformed_fields_fail_the_gate(self, fields: dict, fragment: str) -> None:
        entry = replace(self.ENTRY, **fields)
        findings = gate.validate_sweep_exclusions({"X": entry})
        assert any(fragment in finding for finding in findings), findings
        code, report = evaluate(
            _all_good(),
            external_check_runs=_ALL_EXTERNAL_GREEN,
            sweep_exclusions={"X": entry},
            now=self.NOW,
        )
        assert code == EXIT_FAILURE, report
        assert "external sweep exclusion registry REFUSED" in report
        assert fragment in report

    def test_wrong_entry_type_is_refused_without_crashing(self) -> None:
        registry = {"X": {"reason": "untyped exception"}}
        assert gate.validate_sweep_exclusions(registry) == [
            "X: not a SweepExclusion instance"
        ]
        code, report = evaluate(
            _all_good(),
            external_check_runs=_ALL_EXTERNAL_GREEN,
            sweep_exclusions=registry,
            now=self.NOW,
        )
        assert code == EXIT_FAILURE, report
        assert "external sweep exclusion registry REFUSED" in report

    @pytest.mark.parametrize(("days", "valid"), [(90, True), (91, False)])
    def test_window_cap_boundary(self, days: int, valid: bool) -> None:
        assert gate.SWEEP_EXCLUSION_MAX_DAYS == 90
        expiry = (self.NOW + timedelta(days=days)).date().isoformat()
        findings = gate.validate_sweep_exclusions(
            {"X": replace(self.ENTRY, expires=expiry)}
        )
        assert (not findings) == valid

    @pytest.mark.parametrize(
        ("observation", "expected"),
        [
            (datetime(2026, 12, 19, 23, 59, 59, tzinfo=UTC), EXIT_SUCCESS),
            (datetime(2026, 12, 20, tzinfo=UTC), EXIT_FAILURE),
            (datetime(2026, 12, 21, tzinfo=UTC), EXIT_FAILURE),
            (None, EXIT_FAILURE),
        ],
    )
    def test_expiry_and_missing_clock_rearm_the_sweep(
        self, observation: datetime | None, expected: int
    ) -> None:
        rows = [*_ALL_EXTERNAL_GREEN, _check_run("Unregistered Gate", "failure")]
        code, report = evaluate(
            _all_good(),
            external_check_runs=rows,
            sweep_exclusions={"Unregistered Gate": self.ENTRY},
            now=observation,
        )
        assert code == expected, report
        if expected == EXIT_FAILURE:
            assert "EXPIRED (no longer excluding): Unregistered Gate" in report
            assert "Unregistered Gate (failure)" in report
        else:
            assert "exclusions applied: Unregistered Gate" in report

    def test_exclusion_cannot_override_layer_four(self) -> None:
        name = EXPECTED_EXTERNAL_CONTEXTS[0]
        rows = [
            _check_run(n, "failure" if n == name else "success")
            for n in EXPECTED_EXTERNAL_CONTEXTS
        ]
        code, report = evaluate(
            _all_good(),
            external_check_runs=rows,
            sweep_exclusions={name: self.ENTRY},
            now=self.NOW,
        )
        assert code == EXIT_FAILURE, report
        assert f"L4 external contexts not success (coverage gap): {name}" in report


class TestSweepIsWiredIntoProductionPoller:
    """OMN-17427: fixture files must exercise layer 5 through main()."""

    @staticmethod
    def _main(tmp_path: Path, rows: list[dict], runs: object) -> int:
        jobs_file = tmp_path / "jobs.json"
        checks_file = tmp_path / "check_runs.json"
        runs_file = tmp_path / "workflow_runs.json"
        jobs_file.write_text(json.dumps(_all_good()), encoding="utf-8")
        checks_file.write_text(json.dumps({"check_runs": rows}), encoding="utf-8")
        runs_file.write_text(json.dumps(runs), encoding="utf-8")
        return gate.main(
            [
                "--jobs-file",
                str(jobs_file),
                "--external-check-runs-file",
                str(checks_file),
                "--workflow-runs-file",
                str(runs_file),
                "--event-name",
                "pull_request",
            ]
        )

    @pytest.mark.parametrize("wrapped", [False, True])
    def test_red_pr_check_fails_and_green_or_non_pr_passes(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], wrapped: bool
    ) -> None:
        row = {
            **_check_run("Unregistered Gate", "failure"),
            "details_url": "https://github.com/OmniNode-ai/omnibase_core/actions/runs/777/job/9",
        }
        for event, conclusion, expected in [
            ("pull_request", "failure", EXIT_FAILURE),
            ("pull_request", "success", EXIT_SUCCESS),
            ("schedule", "failure", EXIT_SUCCESS),
        ]:
            row["conclusion"] = conclusion
            runs = [{"id": 777, "event": event}]
            code = self._main(
                tmp_path,
                [*_ALL_EXTERNAL_GREEN, row],
                {"workflow_runs": runs} if wrapped else runs,
            )
            report = capsys.readouterr().out
            assert code == expected, report
            if expected == EXIT_FAILURE:
                assert "Unregistered Gate (failure)" in report

    @pytest.mark.parametrize(
        "runs", [None, {"workflow_runs": "bad"}, [{"id": 888, "event": "schedule"}]]
    )
    def test_unusable_or_missing_index_cannot_exempt_red(
        self, tmp_path: Path, runs: object
    ) -> None:
        row = {
            **_check_run("Unregistered Gate", "failure"),
            "details_url": "https://github.com/OmniNode-ai/omnibase_core/actions/runs/777/job/9",
        }
        assert self._main(tmp_path, [*_ALL_EXTERNAL_GREEN, row], runs) == EXIT_FAILURE

    def test_main_passes_its_clock_to_both_exclusions_and_grace(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        observation = datetime(2026, 10, 17, 12, tzinfo=UTC)

        class FixedClock(datetime):
            @classmethod
            def now(cls, tz: object = None) -> datetime:
                assert tz is UTC
                return observation

        monkeypatch.setattr(gate, "datetime", FixedClock)
        excluded = _check_run("Enable Auto-Merge", "skipped")
        rows = [*_ALL_EXTERNAL_GREEN, excluded]
        # Without a clock the same exclusion is deliberately inactive.
        assert evaluate(_all_good(), external_check_runs=rows)[0] == EXIT_FAILURE
        assert self._main(tmp_path, rows, []) == EXIT_SUCCESS
        row = _check_run(
            "Unregistered Gate", "cancelled", completed_at="2026-10-17T11:59:30Z"
        )
        rows.append(row)
        assert evaluate(_all_good(), external_check_runs=rows)[0] == EXIT_FAILURE
        assert self._main(tmp_path, rows, []) == EXIT_PENDING
        assert (
            "external sweep rows awaiting an automatic replacement"
            in capsys.readouterr().out
        )
        row["completed_at"] = "2026-10-16T12:00:00Z"
        assert self._main(tmp_path, rows, []) == EXIT_FAILURE

    def test_workflow_fetches_full_head_pages_and_passes_both_files(self) -> None:
        workflow = yaml.safe_load(CI_YML.read_text())
        step = next(
            step["run"]
            for step in workflow["jobs"]["ci-summary"]["steps"]
            if "ci_summary_gate.py" in str(step.get("run", ""))
        )
        lines = step.splitlines()
        for endpoint in [
            "commits/${COMMIT_SHA}/check-runs?per_page=100",
            "actions/runs?head_sha=${COMMIT_SHA}&per_page=100",
        ]:
            endpoint_line = next(i for i, line in enumerate(lines) if endpoint in line)
            assert "fetch_with_budget api --paginate" in lines[endpoint_line - 1]
        assert "--external-check-runs-file external_check_runs.json" in step
        assert "--workflow-runs-file workflow_runs.json" in step

    def test_cli_exit_code_matches_the_swept_verdict(self, tmp_path: Path) -> None:
        row = _check_run("Unregistered Gate", "failure")
        for conclusion, expected in [
            ("failure", EXIT_FAILURE),
            ("success", EXIT_SUCCESS),
        ]:
            row["conclusion"] = conclusion
            assert self._main(tmp_path, [*_ALL_EXTERNAL_GREEN, row], []) == expected
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/ci/ci_summary_gate.py",
                    "--jobs-file",
                    str(tmp_path / "jobs.json"),
                    "--external-check-runs-file",
                    str(tmp_path / "check_runs.json"),
                    "--workflow-runs-file",
                    str(tmp_path / "workflow_runs.json"),
                    "--event-name",
                    "pull_request",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == expected, result.stdout + result.stderr

    @pytest.mark.parametrize("contents", [None, "invalid JSON"])
    def test_unreadable_runs_file_still_sweeps(
        self, tmp_path: Path, contents: str | None
    ) -> None:
        row = _check_run("Unregistered Gate", "failure")
        assert self._main(tmp_path, [*_ALL_EXTERNAL_GREEN, row], []) == EXIT_FAILURE
        path = tmp_path / "workflow_runs.json"
        if contents is None:
            path.unlink()
        else:
            path.write_text(contents, encoding="utf-8")
        assert (
            gate.main(
                [
                    "--jobs-file",
                    str(tmp_path / "jobs.json"),
                    "--external-check-runs-file",
                    str(tmp_path / "check_runs.json"),
                    "--workflow-runs-file",
                    str(path),
                    "--event-name",
                    "pull_request",
                ]
            )
            == EXIT_FAILURE
        )
