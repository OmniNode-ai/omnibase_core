# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The shadow-metrics harvester survives a rejected push to ci-shadow-metrics (OMN-19998).

``shadow-metrics-harvest.yml`` runs after every pull-request CI run and appends a
record to the ``ci-shadow-metrics`` branch with one ``git push``. On 2026-11-04 that
push was rejected by GitHub itself (``remote: fatal error in commit_refs`` /
``[remote rejected] ... (failure)``) and the job went red. Because the workflow is
``workflow_run``-triggered, its check lands on the default branch tip, so the
rejection read as a red ``dev``. The record had already been appended locally; nothing
in the repository was wrong.

The job now re-syncs to the remote branch and retries the push a bounded number of
times, and still fails loudly when every attempt is rejected. These tests run the
step's own shell against a local bare repository, so they exercise the push path the
way the workflow wires it, with the GitHub URL redirected by git's ``insteadOf``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "shadow-metrics-harvest.yml"
APPEND_SCRIPT = REPO_ROOT / "scripts" / "ci" / "shadow_metrics_append.py"
STEP_NAME = "Append records to ci-shadow-metrics NDJSON"
BRANCH = "ci-shadow-metrics"
REPOSITORY = "OmniNode-ai/omnibase_core"
MAX_ATTEMPTS = 4


def _step_script() -> str:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    for step in data["jobs"]["harvest"]["steps"]:
        if step.get("name") == STEP_NAME:
            return str(step["run"])
    raise AssertionError(f"{WORKFLOW.name}: step {STEP_NAME!r} not found")


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _reject_first_pushes(bare: Path, count: int) -> None:
    """Install a pre-receive hook that rejects the first ``count`` pushes."""
    counter = bare / "rejections"
    counter.write_text("0", encoding="utf-8")
    hook = bare / "hooks" / "pre-receive"
    hook.write_text(
        "#!/bin/sh\n"
        f'n=$(cat "{counter}")\n'
        f'if [ "$n" -lt {count} ]; then\n'
        f'  echo $((n + 1)) > "{counter}"\n'
        "  echo 'fatal error in commit_refs' >&2\n"
        "  exit 1\n"
        "fi\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)


def _make_bare_with_branch(tmp_path: Path) -> Path:
    bare = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    subprocess.run(
        ["git", "init", "--bare", str(bare)],
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "init", str(seed)],
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
    )
    _git("checkout", "-b", BRANCH, cwd=seed)
    (seed / "README.md").write_text("# metrics\n", encoding="utf-8")
    _git("add", "README.md", cwd=seed)
    _git(
        "-c", "user.name=seed", "-c", "user.email=seed@example.invalid",
        "commit", "-m", "seed",
        cwd=seed,
    )  # fmt: skip
    _git("push", str(bare), BRANCH, cwd=seed)
    return bare


def _run_step(tmp_path: Path, bare: Path) -> subprocess.CompletedProcess[str]:
    work = tmp_path / "work"
    (work / "scripts" / "ci").mkdir(parents=True)
    shutil.copy(APPEND_SCRIPT, work / "scripts" / "ci" / APPEND_SCRIPT.name)
    (work / "records" / "shadow-record-1").mkdir(parents=True)
    (work / "records" / "shadow-record-1" / "shadow_record.json").write_text(
        json.dumps({"repo": REPOSITORY, "head_sha": "a" * 40, "pr_number": 1}),
        encoding="utf-8",
    )
    token = "test-token"
    auth_url = f"https://x-access-token:{token}@github.com/{REPOSITORY}.git"
    env = {
        **scrub_git_location_env(),
        "GH_TOKEN": token,
        "APP_TOKEN": token,
        "NDJSON_PATH": "shadow_metrics.ndjson",
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_WORKFLOW": "Shadow Metrics Harvest",
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_RUN_ID": "1",
        "HARVEST_PUSH_RETRY_DELAY": "0",
        # Redirect the credentialed GitHub URL to the local bare repository.
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": f"url.{bare}.insteadOf",
        "GIT_CONFIG_VALUE_0": auth_url,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    }
    return subprocess.run(
        ["bash", "-e", "-c", _step_script()],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _remote_ndjson(bare: Path) -> list[dict[str, object]]:
    out = _git("show", f"{BRANCH}:shadow_metrics.ndjson", cwd=bare)
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def test_step_script_is_valid_bash() -> None:
    subprocess.run(
        ["bash", "-n", "-c", _step_script()], check=True, capture_output=True
    )


def test_clean_push_lands_the_record_once(tmp_path: Path) -> None:
    bare = _make_bare_with_branch(tmp_path)

    result = _run_step(tmp_path, bare)

    assert result.returncode == 0, result.stderr
    assert len(_remote_ndjson(bare)) == 1


def test_a_rejected_push_is_retried_and_lands_exactly_one_record(
    tmp_path: Path,
) -> None:
    bare = _make_bare_with_branch(tmp_path)
    _reject_first_pushes(bare, count=2)

    result = _run_step(tmp_path, bare)

    assert result.returncode == 0, result.stderr
    assert (bare / "rejections").read_text(encoding="utf-8").strip() == "2"
    records = _remote_ndjson(bare)
    assert len(records) == 1, records


def test_the_job_still_fails_when_every_attempt_is_rejected(tmp_path: Path) -> None:
    bare = _make_bare_with_branch(tmp_path)
    _reject_first_pushes(bare, count=MAX_ATTEMPTS + 10)

    result = _run_step(tmp_path, bare)

    assert result.returncode != 0
    assert (bare / "rejections").read_text(encoding="utf-8").strip() == str(
        MAX_ATTEMPTS
    )
    shown = _git("show", f"{BRANCH}:README.md", cwd=bare)
    assert shown == "# metrics\n"
    with pytest.raises(subprocess.CalledProcessError):
        _git("show", f"{BRANCH}:shadow_metrics.ndjson", cwd=bare)
