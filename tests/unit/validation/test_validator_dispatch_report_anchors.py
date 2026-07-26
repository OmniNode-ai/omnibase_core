# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for check_dispatch_report_content_anchors (OMN-15161).

Ported from steel_onslaught PR #213's
``tests/scripts/test_check_report_contract.py`` content-anchor suite.

Builds a throwaway REAL git repo (for every ``*_sha`` content anchor -- an
actual commit whose SHA either does or does not appear in the fixture repo's
history) and real files on disk under a real repo root (for every
``*_paths`` content anchor), then drives the real
``check_dispatch_report_content_anchors`` entrypoint end to end -- no mocks,
no stubbing of ``git`` or the filesystem. Every RED case is a seeded fixture
proving the gate actually fires through the real validation path.

Git subprocess calls in this file pass ``env=scrub_git_location_env(...)``
per ``omnibase_core.validators.no_unguarded_git_subprocess`` (OMN-14891):
git exports ``GIT_DIR``/``GIT_WORK_TREE``/``GIT_INDEX_FILE``/``GIT_COMMON_DIR``
into every hook environment, and a fixture that shells out to git via
``-C``/``cwd`` without stripping those inherits them, silently retargeting
the real invoking worktree. (The production ``_sha_resolves`` in
``validator_dispatch_report_anchors.py`` uses an explicit ``--git-dir`` flag
instead, which wins over the inherited env var by git's own argument
precedence -- verified empirically -- so it does not need the same guard.)
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from omnibase_core.models.dispatch.report.model_dispatch_report_implementer import (
    ModelDispatchReportImplementer,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_lander import (
    ModelDispatchReportLander,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_scout import (
    ModelDispatchReportScout,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_verifier import (
    ModelDispatchReportVerifier,
)
from omnibase_core.validation.validator_dispatch_report_anchors import (
    check_dispatch_report_content_anchors,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

_SUBSTANTIVE_SUMMARY = (
    "Implemented the golden-chain report contract module and CLI validator, "
    "added seeded RED/GREEN tests per role, and confirmed ruff/mypy/pytest "
    "all pass locally before opening the PR."
)


# --------------------------------------------------------------------------
# Fixture helpers -- real git repo, real files, real report JSON
# --------------------------------------------------------------------------


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
        env=scrub_git_location_env(os.environ),
    )
    return result.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")


def _commit_file(repo: Path, relpath: str, content: str) -> str:
    """Write and commit ``relpath`` inside ``repo``; return the new commit sha."""
    path = repo / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(repo, "add", relpath)
    _git(repo, "commit", "-q", "-m", f"commit {relpath}")
    return _git(repo, "log", "-1", "--format=%H").strip()


def _blob_sha(repo: Path, relpath: str) -> str:
    """Return the git BLOB object id (not a commit) for a committed path."""
    return _git(repo, "rev-parse", f"HEAD:{relpath}").strip()


def _implementer_report(
    *, head_sha: str, files_changed_paths: list[str]
) -> ModelDispatchReportImplementer:
    return ModelDispatchReportImplementer.model_validate_json(
        json.dumps(
            {
                "role": "implementer",
                "pr_number": 1,
                "branch": "b",
                "head_sha": head_sha,
                "verdict": "implemented",
                "files_changed_paths": files_changed_paths,
                "summary": _SUBSTANTIVE_SUMMARY,
            }
        )
    )


# --------------------------------------------------------------------------
# Fail-closed: content anchor present, checking context withheld
# --------------------------------------------------------------------------


def test_fails_closed_when_git_dir_withheld(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    sha = _commit_file(repo, "a.txt", "x\n")
    report = _implementer_report(head_sha=sha, files_changed_paths=["a.txt"])

    violations = check_dispatch_report_content_anchors(
        report, git_dir=None, repo_root=repo
    )

    assert any("head_sha" in v and "git_dir was not provided" in v for v in violations)


def test_fails_closed_when_repo_root_withheld(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    sha = _commit_file(repo, "a.txt", "x\n")
    report = _implementer_report(head_sha=sha, files_changed_paths=["a.txt"])

    violations = check_dispatch_report_content_anchors(
        report, git_dir=repo / ".git", repo_root=None
    )

    assert any(
        "files_changed_paths" in v and "repo_root was not provided" in v
        for v in violations
    )


def test_fails_closed_when_both_withheld_not_silently_skipped(tmp_path: Path) -> None:
    """A perfectly well-shaped report with no checking context supplied at all
    must FAIL, not silently pass -- an unchecked content anchor is not a
    validated one.
    """
    repo = tmp_path / "repo"
    _init_repo(repo)
    sha = _commit_file(repo, "a.txt", "x\n")
    report = _implementer_report(head_sha=sha, files_changed_paths=["a.txt"])

    violations = check_dispatch_report_content_anchors(
        report, git_dir=None, repo_root=None
    )

    assert len(violations) == 2


# --------------------------------------------------------------------------
# GREEN: every anchor resolves against a real repo
# --------------------------------------------------------------------------


def test_all_clean_on_real_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    sha = _commit_file(repo, "a.txt", "x\n")
    report = _implementer_report(head_sha=sha, files_changed_paths=["a.txt"])

    violations = check_dispatch_report_content_anchors(
        report, git_dir=repo / ".git", repo_root=repo
    )

    assert violations == []


# --------------------------------------------------------------------------
# RED: SHA does not resolve
# --------------------------------------------------------------------------


def test_fails_when_sha_does_not_resolve(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit_file(repo, "a.txt", "x\n")
    fabricated_sha = "0" * 40
    report = _implementer_report(head_sha=fabricated_sha, files_changed_paths=["a.txt"])

    violations = check_dispatch_report_content_anchors(
        report, git_dir=repo / ".git", repo_root=repo
    )

    assert any(
        "head_sha" in v and "does not resolve to a real commit" in v for v in violations
    )


def test_fails_when_sha_resolves_to_a_blob_not_a_commit(tmp_path: Path) -> None:
    """A blob hash is a real object in the repo's git dir, but it is not a
    commit -- a "*_sha" content anchor must reject it, not just check that
    SOME object with that hash exists (plain `cat-file -e` without a `^{commit}`
    peel accepts blobs/trees/tags too)."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit_file(repo, "a.txt", "x\n")
    blob_sha = _blob_sha(repo, "a.txt")
    report = _implementer_report(head_sha=blob_sha, files_changed_paths=["a.txt"])

    violations = check_dispatch_report_content_anchors(
        report, git_dir=repo / ".git", repo_root=repo
    )

    assert any(
        "head_sha" in v and "does not resolve to a real commit" in v for v in violations
    )


# --------------------------------------------------------------------------
# RED: artifact path escapes repo_root
# --------------------------------------------------------------------------


def test_rejects_relative_traversal_outside_repo_root(tmp_path: Path) -> None:
    """A '../../../../../../../etc/hosts'-style artifact path must never pass
    just because it happens to resolve to a real file outside the repo --
    containment under repo_root is required, not mere existence.
    """
    repo = tmp_path / "nested" / "worktree" / "repo"
    _init_repo(repo)
    sha = _commit_file(repo, "a.txt", "x\n")
    report = _implementer_report(
        head_sha=sha, files_changed_paths=["../../../../../../../etc/hosts"]
    )

    violations = check_dispatch_report_content_anchors(
        report, git_dir=repo / ".git", repo_root=repo
    )

    assert any(
        "escapes" in v and "etc/hosts" in v and "files_changed_paths" in v
        for v in violations
    )


def test_rejects_absolute_path_escape(tmp_path: Path) -> None:
    """An absolute artifact path silently discards repo_root under plain
    pathlib '/' semantics (``repo_root / "/etc/hosts" == Path("/etc/hosts")``)
    -- this must be caught as an escape, same as a relative traversal.
    """
    repo = tmp_path / "repo"
    _init_repo(repo)
    sha = _commit_file(repo, "a.txt", "x\n")
    report = _implementer_report(head_sha=sha, files_changed_paths=["/etc/hosts"])

    violations = check_dispatch_report_content_anchors(
        report, git_dir=repo / ".git", repo_root=repo
    )

    assert any("escapes" in v and "files_changed_paths" in v for v in violations)


# --------------------------------------------------------------------------
# RED: artifact path does not exist under repo_root
# --------------------------------------------------------------------------


def test_fails_when_artifact_path_does_not_exist(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    sha = _commit_file(repo, "a.txt", "x\n")
    report = _implementer_report(
        head_sha=sha, files_changed_paths=["this_file_was_never_written.py"]
    )

    violations = check_dispatch_report_content_anchors(
        report, git_dir=repo / ".git", repo_root=repo
    )

    assert any(
        "does not exist under repo_root" in v and "this_file_was_never_written.py" in v
        for v in violations
    )


def test_fails_when_artifact_path_resolves_to_a_directory(tmp_path: Path) -> None:
    """A directory satisfies containment and existence but anchors no actual
    artifact -- ``["."]``/``[""]`` (or any subdirectory) must be rejected,
    including the degenerate case of citing repo_root itself."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    sha = _commit_file(repo, "subdir/a.txt", "x\n")
    report = _implementer_report(head_sha=sha, files_changed_paths=["."])

    violations = check_dispatch_report_content_anchors(
        report, git_dir=repo / ".git", repo_root=repo
    )

    assert any("files_changed_paths" in v and "is not a file" in v for v in violations)


def test_fails_when_artifact_path_resolves_to_a_subdirectory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    sha = _commit_file(repo, "subdir/a.txt", "x\n")
    report = _implementer_report(head_sha=sha, files_changed_paths=["subdir"])

    violations = check_dispatch_report_content_anchors(
        report, git_dir=repo / ".git", repo_root=repo
    )

    assert any("files_changed_paths" in v and "is not a file" in v for v in violations)


# --------------------------------------------------------------------------
# Generic over role -- the *_sha/*_paths suffix convention, not per-role code
# --------------------------------------------------------------------------


def test_generic_over_role_verifier(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    sha = _commit_file(repo, "docs/evidence/SO-9999.md", "# fixture evidence\n")
    report = ModelDispatchReportVerifier.model_validate_json(
        json.dumps(
            {
                "role": "verifier",
                "pr_number": 4821,
                "verified_sha": sha,
                "verdict": "confirmed",
                "evidence_paths": ["docs/evidence/SO-9999.md"],
                "summary": _SUBSTANTIVE_SUMMARY,
            }
        )
    )
    assert (
        check_dispatch_report_content_anchors(
            report, git_dir=repo / ".git", repo_root=repo
        )
        == []
    )

    fabricated = ModelDispatchReportVerifier.model_validate_json(
        json.dumps(
            {
                "role": "verifier",
                "pr_number": 4821,
                "verified_sha": "f" * 40,
                "verdict": "confirmed",
                "evidence_paths": ["docs/evidence/SO-9999.md"],
                "summary": _SUBSTANTIVE_SUMMARY,
            }
        )
    )
    violations = check_dispatch_report_content_anchors(
        fabricated, git_dir=repo / ".git", repo_root=repo
    )
    assert any("verified_sha" in v and "does not resolve" in v for v in violations)


def test_generic_over_role_lander(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    sha = _commit_file(repo, "a.txt", "x\n")
    report = ModelDispatchReportLander.model_validate_json(
        json.dumps(
            {
                "role": "lander",
                "pr_number": 4821,
                "merge_sha": sha,
                "verdict": "merged",
                "summary": _SUBSTANTIVE_SUMMARY,
            }
        )
    )
    assert (
        check_dispatch_report_content_anchors(
            report, git_dir=repo / ".git", repo_root=repo
        )
        == []
    )


def test_generic_over_role_scout(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit_file(repo, "src/steel_onslaught/contracts/incentive.py", "# fixture\n")
    report = ModelDispatchReportScout.model_validate_json(
        json.dumps(
            {
                "role": "scout",
                "verdict": "found",
                "findings_paths": ["src/steel_onslaught/contracts/incentive.py"],
                "summary": _SUBSTANTIVE_SUMMARY,
            }
        )
    )
    assert (
        check_dispatch_report_content_anchors(report, git_dir=None, repo_root=repo)
        == []
    )

    missing = ModelDispatchReportScout.model_validate_json(
        json.dumps(
            {
                "role": "scout",
                "verdict": "not_found",
                "findings_paths": ["src/steel_onslaught/contracts/does_not_exist.py"],
                "summary": _SUBSTANTIVE_SUMMARY,
            }
        )
    )
    violations = check_dispatch_report_content_anchors(
        missing, git_dir=None, repo_root=repo
    )
    assert any("does not exist under repo_root" in v for v in violations)
