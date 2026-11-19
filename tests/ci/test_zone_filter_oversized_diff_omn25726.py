# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The reusable zone-filter must list a PR's own files, never the base drift (OMN-25726).

``.github/workflows/zone-filter.yml`` computes the changed-file list on a
``pull_request`` run and hands it to the classifier step through one
environment variable. The runner checks out the PR's *merge* commit, and the
step diffed ``base.sha...HEAD`` where ``base.sha`` is the base tip recorded at
the PR's last event. For a PR whose base has since moved on, that diff holds
every file the base branch changed in between, not only the PR's own. Past
128 KiB (the kernel's limit for one environment string) the classifier step
cannot start at all: bash fails with "Argument list too long", the required
check reads red, and it stays red on every re-run until the PR is rebased.

These tests run the workflow's real "Compute changed files" step in a
throwaway git repository that reproduces that shape, so they fail on a step
that diffs against the drifted merge commit and pass on one that diffs the
PR's own head.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
REUSABLE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "zone-filter.yml"

# One environment string may not exceed 128 KiB (MAX_ARG_STRLEN), so the file
# list that reaches the classifier step has to stay below it.
ENV_STRING_LIMIT = 131072
LONG_NAME = "x" * 200

# A full replacement environment, passed through the repo's git scrub: nothing
# is inherited from the invoking process, so a hook's GIT_DIR / GIT_WORK_TREE
# can never redirect these repositories onto the real worktree.
BASE_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "LC_ALL": "C",
    "HOME": "/nonexistent",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
}


def _diff_step() -> dict[str, Any]:
    workflow = yaml.safe_load(REUSABLE_WORKFLOW.read_text())
    for step in workflow["jobs"]["classify"]["steps"]:
        if step.get("id") == "diff":
            return dict(step)
    raise AssertionError("zone-filter.yml classify job has no step with id 'diff'")


def _render(text: str, contexts: dict[str, str]) -> str:
    """Resolve the ``${{ ... }}`` expressions the step uses against the PR event."""

    def _sub(match: re.Match[str]) -> str:
        expression = match.group(1).strip()
        return contexts.get(expression, "")

    return re.sub(r"\$\{\{(.*?)\}\}", _sub, text)


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args],
        cwd=repo,
        env=scrub_git_location_env(BASE_ENV),
        text=True,
        capture_output=True,
        check=True,
    )
    return done.stdout.strip()


def _commit_files(repo: Path, paths: list[str], message: str) -> str:
    for rel in paths:
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"{rel}\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _run_diff_step(
    tmp_path: Path, *, pr_files: list[str], base_drift_files: list[str]
) -> str:
    """Build a PR whose base drifted, run the real step, return ``changed_files``."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "dev")
    old_base = _commit_files(repo, ["README.md"], "base at PR open")

    _git(repo, "checkout", "-q", "-b", "pr", old_base)
    pr_head = _commit_files(repo, pr_files, "the pull request")

    _git(repo, "checkout", "-q", "dev")
    _commit_files(repo, base_drift_files, "base moves on")

    # The runner checks out the merge of the PR into the CURRENT base tip.
    _git(repo, "checkout", "-q", "--detach", "dev")
    _git(repo, "merge", "-q", "--no-ff", "-m", "merge ref", pr_head)

    github_output = tmp_path / "github_output"
    github_output.write_text("")
    contexts = {
        "github.event_name": "pull_request",
        "github.event.pull_request.base.sha": old_base,
        "github.event.pull_request.head.sha": pr_head,
        "github.event.before": "",
        "github.sha": _git(repo, "rev-parse", "HEAD"),
    }
    step = _diff_step()
    env = {
        **scrub_git_location_env(BASE_ENV),
        **{k: _render(str(v), contexts) for k, v in (step.get("env") or {}).items()},
        "GITHUB_OUTPUT": str(github_output),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "step_summary"),
    }
    subprocess.run(
        ["bash", "-eo", "pipefail", "-c", _render(str(step["run"]), contexts)],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    for line in github_output.read_text().splitlines():
        if line.startswith("changed_files="):
            return line.removeprefix("changed_files=")
    raise AssertionError("the diff step wrote no changed_files output")


def _drift(count: int) -> list[str]:
    return [f"src/drift/{LONG_NAME}_{i}.py" for i in range(count)]


def test_pr_files_are_its_own_when_the_base_has_drifted(tmp_path: Path) -> None:
    changed = _run_diff_step(
        tmp_path, pr_files=["docs/guide.md"], base_drift_files=_drift(800)
    )
    assert changed == "docs/guide.md,", (
        "the step listed files the pull request did not change: "
        f"{len(changed)} characters, starting {changed[:120]!r}"
    )


def test_file_list_handed_to_the_classifier_fits_one_environment_string(
    tmp_path: Path,
) -> None:
    changed = _run_diff_step(
        tmp_path, pr_files=["docs/guide.md"], base_drift_files=_drift(800)
    )
    assert len(changed) < ENV_STRING_LIMIT


def test_a_pr_with_an_oversized_own_diff_gets_the_full_matrix(tmp_path: Path) -> None:
    """An own diff past the limit cannot reach the classifier: no verdict, full matrix.

    An empty list is what the classifier step already reads as "no reliable
    diff" and answers with ``docs_only=false``, the conservative verdict.
    """
    changed = _run_diff_step(
        tmp_path,
        pr_files=_drift(800),
        base_drift_files=["src/other.py"],
    )
    assert changed == ""
