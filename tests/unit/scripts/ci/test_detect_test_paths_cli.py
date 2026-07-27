# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI integration tests for detect_test_paths entry point."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_cli_emits_valid_model_test_selection_json(tmp_path: Path) -> None:
    # A real file (OMN-14921: closure grain needs a real source to build a
    # closure over — cli_bootstrap.py exists in this checkout).
    fake_diff = tmp_path / "diff.txt"
    fake_diff.write_text("src/omnibase_core/cli/cli_bootstrap.py\n")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.ci.detect_test_paths",
            "--changed-files-from",
            str(fake_diff),
            "--ref-name",
            "feature-branch",
            "--event-name",
            "pull_request",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["is_full_suite"] is False
    assert payload["full_suite_reason"] is None
    assert any(p.startswith("tests/unit/cli/") for p in payload["selected_paths"])
    assert "matrix" in payload
    assert isinstance(payload["matrix"], list)


def test_cli_full_suite_on_main(tmp_path: Path) -> None:
    fake_diff = tmp_path / "diff.txt"
    fake_diff.write_text("src/omnibase_core/cli/foo.py\n")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.ci.detect_test_paths",
            "--changed-files-from",
            str(fake_diff),
            "--ref-name",
            "main",
            "--event-name",
            "push",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["is_full_suite"] is True
    assert payload["full_suite_reason"] == "main_branch"
    assert payload["split_count"] == 40


# ---------------------------------------------------------------------------
# OMN-14081: content-aware pyproject.toml classification via --base-ref
# ---------------------------------------------------------------------------

_BASE_PYPROJECT = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "omnibase-core"
version = "0.46.5"
dependencies = ["pydantic>=2.0"]
"""


def _init_repo_with_base_pyproject(repo: Path) -> str:
    """git-init ``repo`` with a committed base pyproject.toml; return the base SHA."""
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "pyproject.toml").write_text(_BASE_PYPROJECT)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    for args in (
        ["init", "-q"],
        ["add", "pyproject.toml"],
        ["commit", "-q", "-m", "base"],
    ):
        subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            env={**env},
            capture_output=True,
        )
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        # OMN-14891: without this, an inherited GIT_DIR from a git hook makes
        # rev-parse report the REAL worktree's HEAD instead of this tmp repo's.
        env=scrub_git_location_env(os.environ),
    ).stdout.strip()


def _run_cli(diff_file: Path, base_ref: str, repo_root: Path) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.ci.detect_test_paths",
            "--changed-files-from",
            str(diff_file),
            "--ref-name",
            "feature-branch",
            "--event-name",
            "pull_request",
            "--base-ref",
            base_ref,
            "--repo-root",
            str(repo_root),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_cli_pyproject_version_bump_narrows(tmp_path: Path) -> None:
    # Real git repo: base pyproject at 0.46.5, working tree bumped to 0.46.6.
    # The CLI reads base via `git show` and head from the working tree, classifies
    # it metadata-only, and must NOT escalate.
    repo = tmp_path / "repo"
    base_sha = _init_repo_with_base_pyproject(repo)
    (repo / "pyproject.toml").write_text(
        _BASE_PYPROJECT.replace('version = "0.46.5"', 'version = "0.46.6"')
    )
    diff_file = tmp_path / "diff.txt"
    diff_file.write_text("pyproject.toml\n")

    payload = _run_cli(diff_file, base_sha, repo)
    assert payload["is_full_suite"] is False
    assert payload["full_suite_reason"] is None


def test_cli_pyproject_dependency_add_escalates(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    base_sha = _init_repo_with_base_pyproject(repo)
    (repo / "pyproject.toml").write_text(
        _BASE_PYPROJECT.replace(
            'dependencies = ["pydantic>=2.0"]',
            'dependencies = ["pydantic>=2.0", "httpx>=0.27"]',
        )
    )
    diff_file = tmp_path / "diff.txt"
    diff_file.write_text("pyproject.toml\n")

    payload = _run_cli(diff_file, base_sha, repo)
    assert payload["is_full_suite"] is True
    assert payload["full_suite_reason"] == "test_infrastructure"


def test_cli_pyproject_without_base_ref_fails_closed(tmp_path: Path) -> None:
    # No --base-ref → classification unavailable → escalate (fail closed).
    diff_file = tmp_path / "diff.txt"
    diff_file.write_text("pyproject.toml\n")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.ci.detect_test_paths",
            "--changed-files-from",
            str(diff_file),
            "--ref-name",
            "feature-branch",
            "--event-name",
            "pull_request",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["is_full_suite"] is True
    assert payload["full_suite_reason"] == "test_infrastructure"
