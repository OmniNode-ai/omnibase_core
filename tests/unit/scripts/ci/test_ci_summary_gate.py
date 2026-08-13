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
import tempfile
from pathlib import Path

import pytest
import yaml

from scripts.ci.ci_summary_gate import (
    EXIT_FAILURE,
    EXIT_PENDING,
    EXIT_SUCCESS,
    EXPECTED_EXTERNAL_CONTEXTS,
    GATE_JOBS,
    SOFT_ALLOWLIST,
    SPEC_REQUIRED_VALIDATOR_JOBS,
    STRICT_SUCCESS_JOBS,
    evaluate,
    evaluate_external,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
CI_YML = WORKFLOWS_DIR / "ci.yml"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _job(
    name: str, conclusion: str | None, *, status: str = "completed", attempt: int = 1
) -> dict:
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "run_attempt": attempt,
    }


def _check_run(
    name: str,
    conclusion: str | None,
    *,
    status: str = "completed",
    started_at: str = "",
) -> dict:
    """Build a ``commits/{sha}/check-runs`` row (L4 external-context fixture)."""
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "started_at": started_at,
    }


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

    def test_allowlisted_version_pin_failure_is_ignored(self) -> None:
        # "Version Pin Compliance" carries continue-on-error and is not a gate
        # need — a failure must NOT block.
        jobs = _all_good() + [_job("Version Pin Compliance", "failure")]
        code, _ = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
        assert code == EXIT_SUCCESS

    def test_allowlisted_orphan_contract_compliance_failure_is_ignored(self) -> None:
        # The orphan "Contract Compliance" job (compliance) is not gated — a
        # failure must NOT block. This must NOT be confused with the gate
        # "Contract Compliance Check".
        jobs = _all_good() + [_job("Contract Compliance", "failure")]
        code, _ = evaluate(jobs, external_check_runs=_ALL_EXTERNAL_GREEN)
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

    def test_neutral_conclusion_is_fail_closed(self) -> None:
        jobs = _all_good() + [_job("Some New Job", "neutral")]
        code, _ = evaluate(jobs)
        assert code == EXIT_FAILURE

    def test_occ_companion_merged_gate_is_strict_and_fails_closed(self) -> None:
        # OMN-15222 (OMN-15214 canary port): the companion-merged gate makes the
        # 2026-07-26 hygiene-sweep trigger state (OPEN companion + MERGED product
        # PR) unreachable via the merge path. It must be a GATE_JOB (CI Summary
        # WAITS for it) AND strict-success (a skip/cancel fails closed) so a
        # red/absent/skipped result can never green the "CI Summary" umbrella —
        # folding into the umbrella instead of adding a new top-level required
        # context avoids the never-reports wedge.
        gate = "OCC Companion Merged Gate (OMN-15214)"
        assert gate in GATE_JOBS
        assert gate in STRICT_SUCCESS_JOBS
        jobs = [j for j in _all_good() if j["name"] != gate]
        jobs.append(_job(gate, "failure"))
        code, report = evaluate(jobs)
        assert code == EXIT_FAILURE
        assert gate in report
        # A skip must also fail closed — the job is unconditional in ci.yml.
        jobs = [j for j in _all_good() if j["name"] != gate]
        jobs.append(_job(gate, "skipped"))
        code, _ = evaluate(jobs)
        assert code == EXIT_FAILURE
        # Absent entirely → PENDING (completeness anchor), never a vacuous green.
        jobs = [j for j in _all_good() if j["name"] != gate]
        code, _ = evaluate(jobs)
        assert code == EXIT_PENDING

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
            [sys.executable, "scripts/ci/ci_summary_gate.py", "--jobs-file", "-"],
            input=json.dumps(_all_good()),
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )
        assert result.returncode == EXIT_PENDING, result.stdout + result.stderr


class TestExpectedExternalContexts:
    """L4 EXPECTED_EXTERNAL_CONTEXTS (enforce-everything gate audit).

    "DB ownership CI twin (B1)" and "LLM refs drift check (OMN-11932)" live in
    separate workflow files (check-db-ownership.yml / check-llm-refs-drift.yml)
    and are therefore invisible to the in-run jobs sweep above; these tests pin
    the resolution against ``commits/{sha}/check-runs`` fixtures directly.
    """

    def test_success_when_both_check_runs_are_green(self) -> None:
        runs = [_check_run(n, "success") for n in EXPECTED_EXTERNAL_CONTEXTS]
        failures, missing = evaluate_external(runs)
        assert failures == []
        assert missing == []

    def test_absent_context_is_missing_not_failure(self) -> None:
        runs = [_check_run(EXPECTED_EXTERNAL_CONTEXTS[0], "success")]
        failures, missing = evaluate_external(runs)
        assert failures == []
        assert missing == [EXPECTED_EXTERNAL_CONTEXTS[1]]

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
            _check_run(EXPECTED_EXTERNAL_CONTEXTS[1], "success"),
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


class TestContractComplianceFailClosed:
    """Static pins for the ci.yml latent fail-open fix.

    contract-compliance's DoD check_values are PR-scoped; its empty-PR_NUMBER
    branch used to `exit 0` -- a vacuous SUCCESS on merge_group/push that
    never ran a single check_value, while GATE_JOBS/STRICT_SUCCESS_JOBS still
    counted it as a provable pass. The `if:` deliberately stays unconditional
    (all three events) rather than narrowing to pull_request-only: since
    "Contract Compliance Check" is a GATE_JOBS entry whose completeness anchor
    accepts a `skipped` conclusion as GOOD, an `if:` that can evaluate false
    would make GitHub post the job as `skipped` on merge_group/push -- a
    *worse* silent-pass than the original bug, via the skip path instead of
    the vacuous-exit-0 path. The reject-required-check-skip-vector pre-commit
    hook (OMN-14863) rejected an earlier draft of this fix that narrowed the
    `if:`, live-confirming this class of regression. The shell logic itself
    can't run outside a real Actions runner, so these pin the source text
    directly.
    """

    def test_contract_compliance_if_stays_unconditional_no_skip_vector(self) -> None:
        # Pins the OMN-14863 skip-vector guard: this job's `if:` must keep
        # admitting pull_request, merge_group, AND push -- narrowing it would
        # let GitHub post a `skipped` conclusion on merge_group/push, which
        # GATE_JOBS' completeness anchor accepts as GOOD (silently worse than
        # the vacuous-exit-0 bug this fix closes). See the class docstring.
        doc = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))
        condition = doc["jobs"]["contract-compliance"]["if"]
        for event in ("pull_request", "merge_group", "push"):
            assert f"github.event_name == '{event}'" in condition, condition

    def test_empty_pr_number_branch_fails_closed_not_open(self) -> None:
        text = CI_YML.read_text(encoding="utf-8")
        marker = 'if [ -z "${PR_NUMBER:-}" ]; then'
        idx = text.index(marker)
        branch = text[idx : idx + 400].split("\n          fi", 1)[0]
        assert "exit 1" in branch, branch
        assert "exit 0" not in branch, branch


class TestContractComplianceNameDistinction:
    def test_orphan_and_gate_contract_compliance_names_never_swap(self) -> None:
        # "Contract Compliance" (the orphan `compliance` job, ci.yml:1036) is
        # advisory-only and must stay in SOFT_ALLOWLIST; "Contract Compliance
        # Check" (the real DoD gate, ci.yml:3374) must stay in GATE_JOBS. A
        # future edit that swaps these two names would silently downgrade the
        # real gate to advisory.
        assert "Contract Compliance" in SOFT_ALLOWLIST
        assert "Contract Compliance Check" not in SOFT_ALLOWLIST
        assert "Contract Compliance Check" in GATE_JOBS
        assert "Contract Compliance" not in GATE_JOBS


# ---------------------------------------------------------------------------
# Fleet-wide completeness-audit classification tables (enforce-everything gate
# audit, omnibase_core priority 7). Every job that can fire on a
# `pull_request` targeting `main`/`dev` in a workflow file OTHER than ci.yml
# (ci.yml's own jobs are covered by the in-run default-deny sweep, opt-out
# only via SOFT_ALLOWLIST -- see the ci_summary_gate.py module docstring) must
# resolve into exactly one of:
#   (a) the shared generic occ-preflight reusable-workflow context, OR
#   (b) EXTERNAL_CONTEXT_FILES (L4 EXPECTED_EXTERNAL_CONTEXTS), OR
#   (c) DIRECT_REQUIRED_JOB_CONTEXTS (a literal context name already directly
#       required on `dev`, per the committed branch-protection snapshot), OR
#   (d) EXPLICIT_EXEMPT_JOBS (a one-line reason).
# A job in a NEW workflow file, or a new job in an existing one, satisfies
# none of these and fails test_every_pr_triggered_job_is_classified until a
# human classifies it -- this is the mechanism that keeps "new workflow file
# = structurally invisible" closed for this repo going forward.
# ---------------------------------------------------------------------------

_OCC_PREFLIGHT_CONTEXT = "occ-preflight / eligibility"

EXTERNAL_CONTEXT_FILES: frozenset[str] = frozenset(
    {"check-db-ownership.yml", "check-llm-refs-drift.yml"}
)

# (file, job_key) -> literal required-status-check context name(s) that job
# resolves to. Each was verified against the live committed snapshot (see
# fixtures/required_status_checks_snapshot.json) at audit time, not guessed;
# test_direct_required_job_contexts_are_all_still_live re-checks every one.
DIRECT_REQUIRED_JOB_CONTEXTS: dict[tuple[str, str], tuple[str, ...]] = {
    ("contract-validation.yml", "contract-validation"): ("contract-validation",),
    ("cr-thread-gate-caller.yml", "gate"): ("gate / CodeRabbit Thread Check",),
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
    ("pr-title-check.yml", "pr-title"): ("pr-title / check-title",),
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
    ("validator-no-unguarded-git-subprocess.yml", "no-unguarded-git-subprocess"): (
        "no-unguarded-git-subprocess",
    ),
    ("validator-runtime-profiles.yml", "runtime-profiles"): ("runtime-profiles",),
    ("check-handshake.yml", "check-handshake"): ("Check architecture handshake",),
    ("canonical-inference-gate.yml", "canonical-inference-gate"): (
        "Canonical Inference Gate",
    ),
    ("call-receipt-gate.yml", "verify"): ("verify / verify",),
    ("call-reject-skip.yml", "call-reject-skip-token"): (
        "call-reject-skip-token / scan / reject-skip-gate-token",
        "call-reject-skip-token / occ-preflight / eligibility",
    ),
    ("call-occ-companion-effect.yml", "occ-companion-effect"): (
        "occ-companion-effect / Publish occ-companion-effect command",
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
    ("propagate-config.yml", "dry-run-ci-check"): (
        "same propagate-config.yml path-scoped rationale as the 'propagate' job above."
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
                if job_key == "occ-preflight" and "occ-preflight.yml" in str(
                    job.get("uses", "")
                ):
                    continue  # shared generic context, see _OCC_PREFLIGHT_CONTEXT
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
        all_named.add(_OCC_PREFLIGHT_CONTEXT)
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
                    if job_key == "occ-preflight":
                        continue
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
