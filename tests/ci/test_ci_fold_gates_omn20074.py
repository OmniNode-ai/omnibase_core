# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20074: verification gates folded into ci.yml under CI Summary.

Three standalone workflow jobs were verification gates whose only enforcing
context was the occ-preflight they embedded. With that preflight gone each one
is a check that runs and cannot fail, so each is folded into ci.yml, whose
required ``CI Summary`` poller fails on any non-allowlisted job of the run:

* ``gate`` (cr-thread-gate-caller.yml), a ``uses:`` caller whose composed
  context ``gate / CodeRabbit Thread Check`` is unchanged;
* ``policy-gate`` (handshake-policy-gate.yml), reached from ci.yml on
  ``merge_group`` only, the one pull-request-reachable event it ever ran on;
* ``dry-run-ci-check`` (propagate-config.yml), now ``propagate-dry-run`` with
  the path filter evaluated inside the run.

The automation jobs auto-merge and propagate are deliberately untouched.
"""

from __future__ import annotations

import shutil
import subprocess
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
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
CI_YML = WORKFLOWS_DIR / "ci.yml"
PROPAGATE_YML = WORKFLOWS_DIR / "propagate-config.yml"
HANDSHAKE_YML = WORKFLOWS_DIR / "handshake-policy-gate.yml"
CR_CALLER_YML = WORKFLOWS_DIR / "cr-thread-gate-caller.yml"
CR_REUSABLE_YML = WORKFLOWS_DIR / "cr-thread-gate.yml"
REQUIRED_CHECKS = REPO_ROOT / ".github" / "required-checks.yaml"

CR_CONTEXT = "gate / CodeRabbit Thread Check"
DRY_RUN_NAME = "Propagate Config Dry-run (OMN-20074)"
HANDSHAKE_CONTEXT = "handshake-policy-gate / Check handshake compliance across repos"
ANCHORED_FOLDS = (CR_CONTEXT, DRY_RUN_NAME)
ALL_FOLDS = (*ANCHORED_FOLDS, HANDSHAKE_CONTEXT)


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _triggers(doc: dict) -> dict:
    # PyYAML 1.1 resolves the bare `on:` key to the boolean True.
    return doc.get("on", doc.get(True)) or {}


def _ci_jobs() -> dict:
    return _load(CI_YML)["jobs"]


def _job(name: str, conclusion: str | None, *, status: str = "completed") -> dict:
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "run_attempt": 1,
    }


def _green_run() -> list[dict]:
    return [_job(n, "success") for n in (*GATE_JOBS, *SPEC_REQUIRED_VALIDATOR_JOBS)]


_EXTERNAL_GREEN: list[dict[str, object]] = [
    {"name": n, "status": "completed", "conclusion": "success", "started_at": ""}
    for n in EXPECTED_EXTERNAL_CONTEXTS
]


# --------------------------------------------------------------------------- #
# gate (cr-thread-gate-caller.yml)
# --------------------------------------------------------------------------- #


def test_cr_thread_gate_caller_workflow_is_gone() -> None:
    assert not CR_CALLER_YML.exists(), (
        "the standalone caller produces the same context as the ci.yml job: a "
        "duplicate producer in a second concurrency group"
    )


def test_cr_thread_gate_is_an_unconditional_caller_in_ci_yml() -> None:
    job = _ci_jobs()["gate"]
    assert job["uses"] == "./.github/workflows/cr-thread-gate.yml"
    # A skipped `uses:` caller never invokes the reusable, so the composed
    # context would not exist at all (OMN-15120/OMN-14864 vector 3).
    assert "if" not in job
    assert "needs" not in job, "no occ-preflight or any other dependency"
    assert "pr-number" in job["with"]
    assert job["secrets"] == {"CROSS_REPO_PAT": "${{ secrets.CROSS_REPO_PAT }}"}


def test_cr_thread_gate_composed_context_is_unchanged() -> None:
    job = _ci_jobs()["gate"]
    inner = _load(CR_REUSABLE_YML)["jobs"]["gate"]["name"]
    assert f"{job.get('name', 'gate')} / {inner}" == CR_CONTEXT
    manifest = yaml.safe_load(REQUIRED_CHECKS.read_text(encoding="utf-8"))
    row = next(g for g in manifest["gates"] if g["name"] == CR_CONTEXT)
    assert row["workflow"] == "ci.yml", "the manifest row must follow the producer"
    assert row["job_path"] == ["gate", "gate"]


# --------------------------------------------------------------------------- #
# policy-gate (handshake-policy-gate.yml)
# --------------------------------------------------------------------------- #


def test_handshake_policy_gate_runs_from_ci_yml_on_merge_group_only() -> None:
    job = _ci_jobs()["handshake-policy-gate"]
    assert job["uses"] == "./.github/workflows/handshake-policy-gate.yml"
    assert job["if"] == "github.event_name == 'merge_group'"
    assert job["permissions"] == {"contents": "read", "actions": "read"}
    inherited = job["secrets"]
    assert inherited == "inherit", "the App-token mint reads org secrets"
    assert "needs" not in job


def test_handshake_policy_gate_workflow_keeps_schedule_and_dispatch() -> None:
    doc = _load(HANDSHAKE_YML)
    triggers = _triggers(doc)
    assert set(triggers) == {"schedule", "workflow_dispatch", "workflow_call"}
    assert doc["permissions"] == {"contents": "read", "actions": "read"}
    assert set(doc["jobs"]) == {"policy-gate"}, "no embedded preflight remains"
    assert "needs" not in doc["jobs"]["policy-gate"]


def test_handshake_policy_gate_context_matches_the_registered_name() -> None:
    caller = _ci_jobs()["handshake-policy-gate"]
    inner = _load(HANDSHAKE_YML)["jobs"]["policy-gate"]["name"]
    assert f"{caller.get('name', 'handshake-policy-gate')} / {inner}" == (
        HANDSHAKE_CONTEXT
    )


# --------------------------------------------------------------------------- #
# dry-run-ci-check (propagate-config.yml)
# --------------------------------------------------------------------------- #


def test_dry_run_job_left_propagate_config() -> None:
    jobs = _load(PROPAGATE_YML)["jobs"]
    assert "dry-run-ci-check" not in jobs
    assert "propagate" in jobs, "the automation job is not part of this change"


def _dry_run_steps() -> list[dict]:
    return _ci_jobs()["propagate-dry-run"]["steps"]


def test_dry_run_job_keeps_the_original_steps_and_token_scope() -> None:
    job = _ci_jobs()["propagate-dry-run"]
    assert job["name"] == DRY_RUN_NAME
    assert "needs" not in job, "no occ-preflight dependency"
    assert "if" not in job, "unconditional: path filtering happens in the steps"
    steps = _dry_run_steps()
    mint = next(s for s in steps if s.get("id") == "app-token")
    execute = next(s for s in steps if s.get("name") == "Execute dry-run")
    assert mint["with"]["app-id"] == "${{ secrets.ONEXBOT_OCC_APP_ID }}"
    assert mint["with"]["permission-contents"] == "read"
    assert "permission-pull-requests" not in mint["with"]
    assert execute["env"]["GITHUB_TOKEN"] == "${{ steps.app-token.outputs.token }}"
    assert execute["env"]["PROPAGATION_NAME"] == "normalization-symmetry-hook"
    assert execute["env"]["PROPAGATION_DRY_RUN"] == "1"
    assert execute["run"].strip() == "bash scripts/propagate-config.sh"


def test_every_step_after_detection_is_gated_on_the_detected_paths() -> None:
    steps = _dry_run_steps()
    detect = next(i for i, s in enumerate(steps) if s.get("id") == "paths")
    assert steps[0]["uses"].startswith("actions/checkout@")
    assert steps[0]["with"]["fetch-depth"] == 0
    for step in steps[detect + 1 :]:
        assert step["if"] == "steps.paths.outputs.changed == 'true'", step


def _detect_script() -> str:
    step = next(s for s in _dry_run_steps() if s.get("id") == "paths")
    return step["run"]


# Nothing is inherited: every subprocess below gets a full replacement
# environment, so GIT_DIR and friends exported by a git hook cannot retarget it.
_TOOL_PATH = ":".join(
    sorted(
        {
            str(Path(found).parent)
            for found in (shutil.which("git"), shutil.which("bash"))
            if found
        }
    )
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env={
            "PATH": _TOOL_PATH,
            "HOME": "/nonexistent",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo_with_change(tmp_path: Path, changed: str) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "dev")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    (repo / "README.md").write_text("base\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    target = repo / changed
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("changed\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "head")
    return repo, base, _git(repo, "rev-parse", "HEAD")


def _run_detection(
    repo: Path,
    *,
    event: str,
    base: str = "",
    before: str = "",
    sha: str = "",
) -> str:
    output = repo.parent / "github_output"
    output.write_text("")
    subprocess.run(
        ["bash", "-e", "-c", _detect_script()],
        cwd=repo,
        env={
            "PATH": _TOOL_PATH,
            "HOME": "/nonexistent",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "EVENT_NAME": event,
            "PR_BASE_SHA": base,
            "PUSH_BEFORE": before,
            "GH_SHA": sha,
            "GITHUB_OUTPUT": str(output),
        },
        check=True,
        capture_output=True,
        text=True,
    )
    return output.read_text().strip()


def _propagation_paths() -> list[str]:
    paths = _triggers(_load(PROPAGATE_YML))["pull_request"]["paths"]
    assert len(paths) >= 5
    return paths


@pytest.mark.parametrize("path", _propagation_paths())
def test_detection_matches_each_original_path_filter_entry(
    tmp_path: Path, path: str
) -> None:
    repo, base, head = _repo_with_change(tmp_path, path)
    assert _run_detection(repo, event="pull_request", base=base) == "changed=true"
    assert _run_detection(repo, event="push", before=base, sha=head) == "changed=true"


def test_detection_ignores_an_unrelated_change(tmp_path: Path) -> None:
    repo, base, head = _repo_with_change(tmp_path, "src/unrelated/module.py")
    assert _run_detection(repo, event="pull_request", base=base) == "changed=false"
    assert _run_detection(repo, event="push", before=base, sha=head) == "changed=false"


def test_detection_runs_on_dispatch_and_skips_events_the_original_never_had(
    tmp_path: Path,
) -> None:
    repo, base, _head = _repo_with_change(tmp_path, "src/unrelated/module.py")
    assert _run_detection(repo, event="workflow_dispatch") == "changed=true"
    assert _run_detection(repo, event="merge_group", base=base) == "changed=false"
    assert _run_detection(repo, event="schedule") == "changed=false"


def test_detection_fails_open_when_no_diff_can_be_computed(tmp_path: Path) -> None:
    repo, _base, head = _repo_with_change(tmp_path, "src/unrelated/module.py")
    zeros = "0" * 40
    assert _run_detection(repo, event="push", before=zeros, sha=head) == "changed=true"
    assert _run_detection(repo, event="pull_request", base="f" * 40) == "changed=true"


# --------------------------------------------------------------------------- #
# CI Summary wiring
# --------------------------------------------------------------------------- #


def test_anchored_folds_are_registered_in_the_completeness_anchor() -> None:
    for name in ANCHORED_FOLDS:
        assert name in GATE_JOBS, name
        assert name in STRICT_SUCCESS_JOBS, name


def test_handshake_policy_gate_is_not_anchored() -> None:
    # Skipped on every pull_request run by design, and a skipped caller of a
    # reusable posts no job under its composed name: anchoring it would hold
    # every pull request PENDING until the poll deadline.
    assert HANDSHAKE_CONTEXT not in GATE_JOBS
    assert HANDSHAKE_CONTEXT not in STRICT_SUCCESS_JOBS


def test_no_fold_hides_behind_the_soft_allowlist() -> None:
    for name in ALL_FOLDS:
        assert name not in SOFT_ALLOWLIST, name


def test_baseline_run_with_the_folds_green_is_success() -> None:
    code, report = evaluate(_green_run(), external_check_runs=_EXTERNAL_GREEN)
    assert code == EXIT_SUCCESS, report


@pytest.mark.parametrize("name", ALL_FOLDS)
def test_a_failing_folded_gate_fails_ci_summary(name: str) -> None:
    """Positive control: the fold is enforced, not merely listed."""
    jobs = [j for j in _green_run() if j["name"] != name] + [_job(name, "failure")]
    code, report = evaluate(jobs, external_check_runs=_EXTERNAL_GREEN)
    assert code == EXIT_FAILURE, report
    assert name in report


@pytest.mark.parametrize("name", ANCHORED_FOLDS)
def test_a_skipped_anchored_fold_fails_closed(name: str) -> None:
    jobs = [j for j in _green_run() if j["name"] != name] + [_job(name, "skipped")]
    code, report = evaluate(jobs, external_check_runs=_EXTERNAL_GREEN)
    assert code == EXIT_FAILURE, report


@pytest.mark.parametrize("name", ANCHORED_FOLDS)
def test_an_absent_anchored_fold_holds_pending(name: str) -> None:
    jobs = [j for j in _green_run() if j["name"] != name]
    code, report = evaluate(jobs, external_check_runs=_EXTERNAL_GREEN)
    assert code == EXIT_PENDING, report


def test_the_anchored_names_are_the_names_the_jobs_api_reports() -> None:
    jobs = _ci_jobs()
    assert jobs["propagate-dry-run"]["name"] == DRY_RUN_NAME
    inner = _load(CR_REUSABLE_YML)["jobs"]["gate"]["name"]
    assert f"gate / {inner}" == CR_CONTEXT
