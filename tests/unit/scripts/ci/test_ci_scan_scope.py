# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Scope decisions for the diff-scoped per-file CI validators (OMN-19614).

Every branch that is not a verified pull request diff must resolve to the full
tracked tree. These tests build a real git repository with GitHub's
pull_request checkout shape (a two-parent merge commit whose first parent is
the base tip and whose second parent is the pull request head) and pin each
fallback.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)
from scripts.ci.ci_scan_scope import MODE_DIFF, MODE_FULL, decide_scope, main

pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
        env=scrub_git_location_env(),
    )
    return result.stdout.strip()


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def pr_repo(tmp_path: Path) -> tuple[Path, str]:
    """A repo checked out at a pull request merge commit.

    Returns the repo and the pull request head sha. The pull request edits
    ``src/a.py``, adds ``src/new.py`` and deletes ``src/gone.py``; the base
    moved on after the branch point by editing ``src/base_only.py``.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "dev")
    _git(repo, "config", "user.email", "ci@example.invalid")
    _git(repo, "config", "user.name", "ci")
    _git(repo, "config", "commit.gpgsign", "false")
    _write(repo, "src/a.py", "a = 1\n")
    _write(repo, "src/gone.py", "gone = 1\n")
    _write(repo, "src/base_only.py", "b = 1\n")
    _write(repo, ".secrets.baseline", "{}\n")
    _write(repo, "docs/readme.md", "# readme\n")
    _commit(repo, "root")

    _git(repo, "checkout", "-q", "-b", "feature")
    _write(repo, "src/a.py", "a = 2\n")
    _write(repo, "src/new.py", "new = 1\n")
    (repo / "src/gone.py").unlink()
    head_sha = _commit(repo, "feature")

    _git(repo, "checkout", "-q", "dev")
    _write(repo, "src/base_only.py", "b = 2\n")
    _commit(repo, "base moves")

    _git(repo, "merge", "-q", "--no-ff", "--no-edit", "feature")
    return repo, head_sha


def test_pull_request_scans_only_the_changed_files(
    pr_repo: tuple[Path, str],
) -> None:
    repo, head_sha = pr_repo

    scope = decide_scope(
        repo=repo, event="pull_request", pr_head_sha=head_sha, force_full=[]
    )

    assert scope.mode == MODE_DIFF
    # The deleted file is not scanned, and neither is the file only the base
    # changed: the merge commit's first parent already carries it.
    assert sorted(scope.files) == ["src/a.py", "src/new.py"]


@pytest.mark.parametrize(
    "event", ["push", "merge_group", "schedule", "workflow_dispatch", ""]
)
def test_every_other_event_scans_the_full_tree(
    pr_repo: tuple[Path, str], event: str
) -> None:
    repo, head_sha = pr_repo

    scope = decide_scope(repo=repo, event=event, pr_head_sha=head_sha, force_full=[])

    assert scope.mode == MODE_FULL
    assert set(scope.files) == set(_git(repo, "ls-files").splitlines())


def test_a_head_that_is_not_the_merge_commit_fails_closed_to_full(
    pr_repo: tuple[Path, str],
) -> None:
    repo, head_sha = pr_repo
    # A checkout of the PR head itself (one parent) must never be read as a
    # diff of its last commit only.
    _git(repo, "checkout", "-q", head_sha)

    scope = decide_scope(
        repo=repo, event="pull_request", pr_head_sha=head_sha, force_full=[]
    )

    assert scope.mode == MODE_FULL
    assert "unresolvable" in scope.reason


def test_a_second_parent_other_than_the_event_head_fails_closed_to_full(
    pr_repo: tuple[Path, str],
) -> None:
    repo, _head_sha = pr_repo

    scope = decide_scope(
        repo=repo,
        event="pull_request",
        pr_head_sha="0" * 40,
        force_full=[],
    )

    assert scope.mode == MODE_FULL
    assert "unresolvable" in scope.reason


def test_a_missing_head_sha_fails_closed_to_full(pr_repo: tuple[Path, str]) -> None:
    repo, _head_sha = pr_repo

    scope = decide_scope(repo=repo, event="pull_request", pr_head_sha="", force_full=[])

    assert scope.mode == MODE_FULL


def test_a_changed_force_full_path_scans_the_full_tree(
    pr_repo: tuple[Path, str],
) -> None:
    repo, head_sha = pr_repo

    scope = decide_scope(
        repo=repo,
        event="pull_request",
        pr_head_sha=head_sha,
        force_full=[".secrets.baseline", "src/new.py"],
    )

    assert scope.mode == MODE_FULL
    assert "src/new.py" in scope.reason


def test_a_deleted_force_full_path_scans_the_full_tree(
    pr_repo: tuple[Path, str],
) -> None:
    repo, head_sha = pr_repo

    scope = decide_scope(
        repo=repo,
        event="pull_request",
        pr_head_sha=head_sha,
        force_full=["src/gone*.py"],
    )

    assert scope.mode == MODE_FULL


def test_an_unchanged_force_full_path_keeps_the_diff_scope(
    pr_repo: tuple[Path, str],
) -> None:
    repo, head_sha = pr_repo

    scope = decide_scope(
        repo=repo,
        event="pull_request",
        pr_head_sha=head_sha,
        # base_only.py changed on the base, not in the pull request.
        force_full=[".secrets.baseline", "src/base_only.py"],
    )

    assert scope.mode == MODE_DIFF


def test_main_writes_a_nul_separated_list(
    pr_repo: tuple[Path, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, head_sha = pr_repo
    out = tmp_path / "files.bin"

    rc = main(
        [
            "--event",
            "pull_request",
            "--pr-head-sha",
            head_sha,
            "--repo",
            str(repo),
            "--nul",
            "--out",
            str(out),
        ]
    )

    assert rc == 0
    assert sorted(out.read_text().split("\0")[:-1]) == ["src/a.py", "src/new.py"]
    stdout = capsys.readouterr().out
    assert "mode=diff files=2" in stdout
    assert "  src/new.py" in stdout


def test_main_writes_an_empty_list_when_nothing_is_scannable(
    pr_repo: tuple[Path, str], tmp_path: Path
) -> None:
    repo, _head_sha = pr_repo
    # A pull request whose only change is a deletion.
    _git(repo, "checkout", "-q", "-b", "delete-only", "dev~1")
    (repo / "docs/readme.md").unlink()
    head_sha = _commit(repo, "delete only")
    _git(repo, "checkout", "-q", "dev")
    _git(repo, "merge", "-q", "--no-ff", "--no-edit", "delete-only")
    out = tmp_path / "files.txt"

    rc = main(
        [
            "--event",
            "pull_request",
            "--pr-head-sha",
            head_sha,
            "--repo",
            str(repo),
            "--out",
            str(out),
        ]
    )

    assert rc == 0
    assert out.read_text() == ""


def test_main_exits_2_outside_a_git_repository(tmp_path: Path) -> None:
    rc = main(
        [
            "--event",
            "push",
            "--repo",
            str(tmp_path),
            "--out",
            str(tmp_path / "files.txt"),
        ]
    )

    assert rc == 2
