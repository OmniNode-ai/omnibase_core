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


def test_snapshot_paths_and_blobs_use_index_and_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git(tmp_path, "init")
    path = "a name\nwith newline.py"
    source = tmp_path / path
    source.write_bytes(b"base\r\n\x00\xff")
    git(tmp_path, "add", "--", path)
    tree = git(tmp_path, "write-tree")
    base = git(tmp_path, "commit-tree", tree, "-m", "base snapshot")
    git(tmp_path, "update-ref", "refs/heads/main", base)
    git(tmp_path, "symbolic-ref", "HEAD", "refs/heads/main")
    source.write_bytes(b"indexed\r\n\x00\xff")
    (tmp_path / "new.py").write_text("new\n")
    git(tmp_path, "add", "-A")
    source.write_text("unstaged\n")
    (tmp_path / "untracked.py").write_text("untracked\n")
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "nonexistent"))
    handler = NodeGitFileListingEffect()
    selected = [path, "new.py", "absent.py", path]
    indexed = handler.handle(
        ModelGitFileListingInput(root=tmp_path, snapshot="index", blob_paths=selected)
    )
    assert set(indexed.paths) == {path, "new.py"}
    assert indexed.blobs == {
        path: b"indexed\r\n\x00\xff",
        "new.py": b"new\n",
        "absent.py": None,
    }
    assert indexed.revision_exists is None
    assert not indexed.has_unmerged_entries
    revision = handler.handle(
        ModelGitFileListingInput(
            root=tmp_path, snapshot="revision", base_ref=base, blob_paths=selected
        )
    )
    assert revision.paths == [path]
    assert revision.blobs == {
        path: b"base\r\n\x00\xff",
        "new.py": None,
        "absent.py": None,
    }
    assert revision.revision_exists is True
    assert not revision.fell_back_to_all


@pytest.mark.parametrize("ref", ["HEAD", "missing-ref", "--all"])
def test_missing_snapshot_revision_has_explicit_evidence(
    tmp_path: Path, ref: str
) -> None:
    git(tmp_path, "init")
    result = NodeGitFileListingEffect().handle(
        ModelGitFileListingInput(
            root=tmp_path, snapshot="revision", base_ref=ref, blob_paths=["absent"]
        )
    )
    assert result.revision_exists is False
    assert result.paths == []
    assert result.blobs == {"absent": None}
    assert not result.fell_back_to_all


def test_index_snapshot_reports_conflicts_and_skips_gitlinks(tmp_path: Path) -> None:
    git(tmp_path, "init")
    blob = git(tmp_path, "hash-object", "-w", "--stdin", content="source\n")
    tree = git(tmp_path, "mktree", content=f"100644 blob {blob}\tclean.py\n")
    commit = git(tmp_path, "commit-tree", tree, "-m", "gitlink target")
    git(
        tmp_path,
        "update-index",
        "--index-info",
        content=(
            f"100644 {blob} 0\tclean.py\n"
            f"100644 {blob} 1\tconflict.py\n"
            f"100644 {blob} 2\tconflict.py\n"
            f"100644 {blob} 3\tconflict.py\n"
            f"160000 {commit} 0\tsubmodule\n"
        ),
    )
    result = NodeGitFileListingEffect().handle(
        ModelGitFileListingInput(
            root=tmp_path,
            snapshot="index",
            blob_paths=["clean.py", "conflict.py", "submodule"],
        )
    )
    assert result.has_unmerged_entries
    assert result.paths == ["clean.py"]
    assert result.blobs == {
        "clean.py": b"source\n",
        "conflict.py": None,
        "submodule": None,
    }
    linked_tree = git(
        tmp_path, "mktree", content=f"160000 commit {commit}\tsubmodule\n"
    )
    linked_commit = git(tmp_path, "commit-tree", linked_tree, "-m", "gitlink snapshot")
    revision = NodeGitFileListingEffect().handle(
        ModelGitFileListingInput(
            root=tmp_path,
            snapshot="revision",
            base_ref=linked_commit,
            blob_paths=["submodule"],
        )
    )
    assert revision.revision_exists
    assert revision.paths == []
    assert revision.blobs == {"submodule": None}


@pytest.mark.parametrize("snapshot", ["index", "revision"])
def test_snapshot_outside_git_fails_closed(tmp_path: Path, snapshot: str) -> None:
    with pytest.raises(ModelOnexError, match="rev-parse"):
        NodeGitFileListingEffect().handle(
            ModelGitFileListingInput.model_validate(
                {"root": tmp_path, "snapshot": snapshot}
            )
        )


def test_missing_tracked_blob_fails_closed(tmp_path: Path) -> None:
    git(tmp_path, "init")
    (tmp_path / "source.py").write_text("tracked source\n")
    git(tmp_path, "add", "source.py")
    object_id = git(tmp_path, "rev-parse", ":source.py")
    (tmp_path / ".git" / "objects" / object_id[:2] / object_id[2:]).unlink()
    with pytest.raises(
        ModelOnexError, match=r"could not read snapshot blob: source\.py"
    ):
        NodeGitFileListingEffect().handle(
            ModelGitFileListingInput(
                root=tmp_path, snapshot="index", blob_paths=["source.py"]
            )
        )
