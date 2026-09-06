# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tracked-repository-root scope tests for the local-paths validator (OMN-17993).

The pre-commit hook that enforces this rule is ``pass_filenames: true``: it
only ever sees the files a commit stages. A repository-root file committed
before the hook existed — or before its pattern matched — is never
re-examined, so ``.mcp.json`` carried an operator-home clone path at HEAD
while the hook reported green on every subsequent commit. Root cause 4.4 of
the OMN-17992 inventory: a gate scoped to part of the tree reports green over
the rest.

``test_extensionless_root_dotfile_is_scanned`` and
``test_repository_root_is_clean_at_head`` are the positive controls: both fail
against the pre-OMN-17993 validator, the first because the extension allowlist
skips an extension-less dotfile in silence, the second because nothing scanned
the tracked root at all.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from omnibase_core.validation.validator_local_paths import (
    ValidatorLocalPaths,
    tracked_root_files,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# Positive-control literals. This module is a fixture corpus for the detector
# under test, so the paths below are deliberate.
OPERATOR_HOME = "/Users/someone/Code/x"  # local-path-ok: control fixture
VOLUME_PATH = "/Volumes/DRIVE/y"  # local-path-ok: control fixture


def _git(repo: Path, *args: str) -> None:
    # A git hook exports GIT_DIR / GIT_WORK_TREE, which override both `cwd=`
    # and `git -C`; without the scrub this fixture would mutate the invoking
    # worktree instead of tmp_path (OMN-14891).
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env=scrub_git_location_env(os.environ),
    )


def _make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for rel, body in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "ci@example.invalid")
    _git(repo, "config", "user.name", "ci")
    _git(repo, "add", "-A", "-f")
    _git(repo, "commit", "-qm", "fixture")
    return repo


def _run_cli(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_local_paths",
            "--tracked-root",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=scrub_git_location_env(os.environ),
    )


@pytest.mark.unit
def test_root_dotfile_with_an_extension_is_scanned(tmp_path: Path) -> None:
    """The live ``.mcp.json`` shape."""
    repo = _make_repo(tmp_path, {".mcp.json": '{"args": ["' + OPERATOR_HOME + '"]}\n'})
    result = _run_cli(repo)
    assert result.returncode == 1, result.stdout
    assert ".mcp.json" in result.stdout


@pytest.mark.unit
def test_extensionless_root_dotfile_is_scanned(tmp_path: Path) -> None:
    """RED against the pre-OMN-17993 validator: ``.envrc`` has no suffix, so
    the extension allowlist skipped it without saying so."""
    repo = _make_repo(tmp_path, {".envrc": f"export ROOT={VOLUME_PATH}\n"})
    validator = ValidatorLocalPaths()
    assert validator.check_file(repo / ".envrc") == []
    assert validator.check_file(repo / ".envrc", ignore_extension_filter=True)

    result = _run_cli(repo)
    assert result.returncode == 1, result.stdout
    assert ".envrc" in result.stdout


@pytest.mark.unit
def test_suppression_marker_still_honoured(tmp_path: Path) -> None:
    repo = _make_repo(
        tmp_path,
        {".envrc": f"export ROOT={VOLUME_PATH}  # local-path-ok\n"},
    )
    result = _run_cli(repo)
    assert result.returncode == 0, result.stdout


@pytest.mark.unit
def test_scan_is_root_only_and_does_not_recurse(tmp_path: Path) -> None:
    """The root scan is a bounded, zero-residue surface; the recursive scan is
    a separate mode with its own (large) pre-existing residue."""
    repo = _make_repo(
        tmp_path,
        {
            "README.md": "clean\n",
            "src/deep.py": f'P = "{OPERATOR_HOME}"\n',
        },
    )
    names = {p.name for p in tracked_root_files(repo)}
    assert names == {"README.md"}
    assert _run_cli(repo).returncode == 0


@pytest.mark.unit
def test_scanned_surface_is_the_tracked_set_not_the_ignore_rules(
    tmp_path: Path,
) -> None:
    """An ignore rule does not untrack an existing path, so ignore state is
    not evidence about what is committed (inventory root cause 4.9)."""
    repo = _make_repo(
        tmp_path,
        {".gitignore": ".mcp.json\n", ".mcp.json": f'{{"p": "{OPERATOR_HOME}"}}\n'},
    )
    assert _run_cli(repo).returncode == 1


@pytest.mark.unit
def test_untracked_root_file_is_not_scanned(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"README.md": "clean\n"})
    (repo / ".scratch").write_text(f"{OPERATOR_HOME}\n", encoding="utf-8")
    assert _run_cli(repo).returncode == 0


@pytest.mark.unit
def test_repository_root_is_clean_at_head() -> None:
    """The live invariant. RED before ``.mcp.json`` was repointed."""
    validator = ValidatorLocalPaths()
    violations = [
        v
        for f in tracked_root_files(REPO_ROOT)
        for v in validator.check_file(f, ignore_extension_filter=True)
    ]
    assert violations == [], "\n".join(
        f"{v.file}:{v.line}: {v.matched_text!r}" for v in violations
    )
