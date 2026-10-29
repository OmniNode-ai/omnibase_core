# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canary for plan task T2.6 (OMN-21498): the pre-commit hooks check, never rewrite.

Each hook converted from a rewriting form is lifted out of ``.pre-commit-config.yaml``
into a throwaway git repository and run through ``pre-commit`` itself on a canary:
an unformatted file, an unused import, a file with no final newline, a staged
``tmp/`` file and a commit message carrying the AI co-author trailer. Every hook
must refuse (exit non-zero) and the working tree must be byte-identical after the
run. A clean control is run through the same hooks and must pass, so a zero is
never a hook that did not run.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_CHECK_ONLY = (
    "ruff-format",
    "ruff-fix",
    "check-end-of-file",
    "reject-staged-tmp-files",
    "reject-ai-coauthor-trailer",
)
_TRAILER = "Co-Authored-By: Claude <noreply@anthropic.com>"


def _hooks() -> dict[str, dict[str, object]]:
    config = yaml.safe_load((_ROOT / ".pre-commit-config.yaml").read_text("utf-8"))
    return {
        hook["id"]: hook for repo in config["repos"] for hook in repo.get("hooks", [])
    }


def _canary_config(tmp_path: Path) -> Path:
    """The five hooks as local hooks, with ``uv run`` dropped (the venv is on PATH)."""
    hooks = _hooks()
    missing = [hook_id for hook_id in _CHECK_ONLY if hook_id not in hooks]
    assert not missing, f"hooks absent from .pre-commit-config.yaml: {missing}"
    lifted = []
    for hook_id in _CHECK_ONLY:
        hook = dict(hooks[hook_id])
        entry = hook.get("entry")
        if isinstance(entry, str) and entry.startswith("uv run "):
            hook["entry"] = entry.removeprefix("uv run ")
        lifted.append(hook)
    path = tmp_path / "canary-config.yaml"
    path.write_text(
        yaml.safe_dump({"repos": [{"repo": "local", "hooks": lifted}]}),
        encoding="utf-8",
    )
    return path


def _tree_digest(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env=scrub_git_location_env(),
    )


def _pre_commit(
    repo: Path, config: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    inherited = scrub_git_location_env()
    env = {
        **inherited,
        "PATH": f"{Path(sys.executable).parent}{os.pathsep}{inherited['PATH']}",
        "PRE_COMMIT_COLOR": "never",
        # ruff's cache is a by-product outside the checked tree, not a rewrite of it.
        "RUFF_CACHE_DIR": str(config.parent / "ruff-cache"),
    }
    return subprocess.run(
        [sys.executable, "-m", "pre_commit", "run", "--config", str(config), *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    root.mkdir()
    subprocess.run(
        ["git", "init", "-q", str(root)], check=True, env=scrub_git_location_env()
    )
    _git(root, "config", "user.email", "canary@example.invalid")
    _git(root, "config", "user.name", "canary")
    return root


def _stage(repo: Path, rel: str, content: bytes) -> None:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    _git(repo, "add", rel)


def test_every_converted_hook_is_check_only_in_the_config() -> None:
    hooks = _hooks()
    assert "end-of-file-fixer" not in hooks
    assert "clean-tmp-directory" not in hooks
    assert "strip-ai-coauthor-trailer" not in hooks
    assert "--fix" not in str(hooks["ruff-fix"]["entry"])
    assert "--check" in str(hooks["ruff-format"]["entry"])


@pytest.mark.parametrize(
    ("hook_id", "rel", "content"),
    [
        ("ruff-format", "src/pkg/bad.py", b"x=1\n"),
        ("ruff-fix", "src/pkg/bad.py", b"import os\n"),
        ("check-end-of-file", "notes.txt", b"no final newline"),
        ("check-end-of-file", "extra.txt", b"two trailing newlines\n\n"),
        ("reject-staged-tmp-files", "tmp/scratch.txt", b"scratch\n"),
    ],
)
def test_canary_is_refused_and_tree_is_byte_identical(
    repo: Path, tmp_path: Path, hook_id: str, rel: str, content: bytes
) -> None:
    config = _canary_config(tmp_path)
    _stage(repo, rel, content)
    before = _tree_digest(repo)
    result = _pre_commit(repo, config, hook_id, "--files", rel)
    assert result.returncode != 0, result.stdout
    assert "Failed" in result.stdout, result.stdout
    assert _tree_digest(repo) == before


def test_unformatted_file_and_trailer_canary_is_refused_whole(
    repo: Path, tmp_path: Path
) -> None:
    """The plan's canary: an unformatted file plus a trailer, refused with the tree untouched."""
    config = _canary_config(tmp_path)
    _stage(repo, "src/pkg/bad.py", b"x=1\n")
    message = repo / "COMMIT_MSG"
    message.write_text(f"feat: canary\n\n{_TRAILER}\n", encoding="utf-8")
    before = _tree_digest(repo)
    files = _pre_commit(repo, config, "--all-files", "--hook-stage", "pre-commit")
    trailer = _pre_commit(
        repo,
        config,
        "reject-ai-coauthor-trailer",
        "--hook-stage",
        "commit-msg",
        "--commit-msg-filename",
        str(message),
    )
    assert files.returncode != 0, files.stdout
    assert trailer.returncode != 0, trailer.stdout
    assert _tree_digest(repo) == before


def test_clean_control_passes_every_hook(repo: Path, tmp_path: Path) -> None:
    """Positive control: formatted, lint-clean, newline-terminated, no tmp/, no trailer."""
    config = _canary_config(tmp_path)
    _stage(repo, "src/pkg/good.py", b"x = 1\n")
    _stage(repo, "notes.txt", b"one final newline\n")
    message = repo / "COMMIT_MSG"
    message.write_text("feat: canary\n\nbody\n", encoding="utf-8")
    before = _tree_digest(repo)
    files = _pre_commit(repo, config, "--all-files", "--hook-stage", "pre-commit")
    trailer = _pre_commit(
        repo,
        config,
        "reject-ai-coauthor-trailer",
        "--hook-stage",
        "commit-msg",
        "--commit-msg-filename",
        str(message),
    )
    assert files.returncode == 0, files.stdout
    assert trailer.returncode == 0, trailer.stdout
    assert "Passed" in files.stdout
    assert _tree_digest(repo) == before
