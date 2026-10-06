# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Listing against a temporary repo built with Git plumbing."""

import subprocess
from pathlib import Path

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.git_file_listing.model_git_file_listing_input import (
    ModelGitFileListingInput,
)
from omnibase_core.nodes.node_git_file_listing_effect.handler import (
    NodeGitFileListingEffect,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit


def git(root: Path, *args: str, content: str | None = None) -> str:
    env = scrub_git_location_env()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Synthetic",
            "GIT_AUTHOR_EMAIL": "synthetic@example.test",
            "GIT_COMMITTER_NAME": "Synthetic",
            "GIT_COMMITTER_EMAIL": "synthetic@example.test",
        }
    )
    return subprocess.run(
        ["git", "-C", str(root), *args],
        input=content,
        text=True,
        capture_output=True,
        check=True,
        env=scrub_git_location_env(env),
    ).stdout.strip()


def test_all_diff_and_missing_ref_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git(tmp_path, "init")
    blob = git(tmp_path, "hash-object", "-w", "--stdin", content="clean\n")
    tree = git(tmp_path, "mktree", content=f"100644 blob {blob}\ttracked.txt\n")
    base = git(tmp_path, "commit-tree", tree, "-m", "synthetic base")
    git(tmp_path, "update-ref", "refs/heads/main", base)
    git(tmp_path, "symbolic-ref", "HEAD", "refs/heads/main")
    tree = git(
        tmp_path,
        "mktree",
        content=f"100644 blob {blob}\ttracked.txt\n100644 blob {blob}\tchanged name.txt\n",
    )
    head = git(tmp_path, "commit-tree", tree, "-p", base, "-m", "synthetic change")
    git(tmp_path, "update-ref", "refs/heads/main", head)
    git(tmp_path, "read-tree", head)
    for name in ("tracked.txt", "changed name.txt", "untracked.txt", "ignored.txt"):
        (tmp_path / name).write_text("clean\n")
    (tmp_path / ".gitignore").write_text("ignored.txt\n")
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "nonexistent"))
    handler = NodeGitFileListingEffect()
    all_files = handler.handle(ModelGitFileListingInput(root=tmp_path))
    assert set(all_files.paths) == {
        "tracked.txt",
        "changed name.txt",
        "untracked.txt",
        ".gitignore",
    }
    assert not all_files.fell_back_to_all
    diff = handler.handle(
        ModelGitFileListingInput(root=tmp_path, scope="diff", base_ref=base)
    )
    assert diff.paths == ["changed name.txt"]
    assert not diff.fell_back_to_all
    unchanged = handler.handle(
        ModelGitFileListingInput(root=tmp_path, scope="diff", base_ref="HEAD")
    )
    assert unchanged.paths == []
    assert not unchanged.fell_back_to_all
    fallback = handler.handle(
        ModelGitFileListingInput(
            root=tmp_path, scope="diff", base_ref="missing-synthetic-ref"
        )
    )
    assert fallback.paths == all_files.paths
    assert fallback.fell_back_to_all


def test_resolve_root_from_nested_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git(tmp_path, "init")
    nested = tmp_path / "nested"
    nested.mkdir()
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "nonexistent"))
    assert NodeGitFileListingEffect().resolve_root(nested) == tmp_path.resolve()


def test_resolve_root_outside_git(tmp_path: Path) -> None:
    assert NodeGitFileListingEffect().resolve_root(tmp_path) == tmp_path.resolve()


def test_listing_failure_is_onex_error(tmp_path: Path) -> None:
    with pytest.raises(ModelOnexError, match="ls-files"):
        NodeGitFileListingEffect().handle(ModelGitFileListingInput(root=tmp_path))
