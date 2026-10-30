# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Read-only Git evidence primitives for flip proofs."""

from __future__ import annotations

from pathlib import Path


def _git_repo_root(path: Path) -> Path | None:
    """Toplevel of the git repo that owns ``path`` (works cross-repo for fan-out)."""
    import subprocess

    start = path if path.is_dir() else path.parent
    try:
        proc = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    root = proc.stdout.strip()
    return Path(root) if root else None


def _git_show(repo_root: Path, ref: str, rel_path: str) -> str | None:
    """``git show <ref>:<rel_path>`` in ``repo_root``; None if absent/unresolvable."""
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{ref}:{rel_path}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def _git_ref_exists(repo_root: Path, ref: str) -> bool:
    import subprocess

    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "rev-parse",
                "--verify",
                "--quiet",
                f"{ref}^{{commit}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return proc.returncode == 0


def _git_ls_tree(repo_root: Path, ref: str, rel_dir: str) -> list[str] | None:
    """Sorted repo-relative file paths under ``rel_dir`` at ``ref``; None on error."""
    import subprocess

    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "ls-tree",
                "-r",
                "--name-only",
                ref,
                "--",
                rel_dir,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return sorted(line.strip() for line in proc.stdout.splitlines() if line.strip())


def _git_is_ancestor(repo_root: Path, ancestor: str, ref: str = "HEAD") -> bool:
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", ancestor, ref],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return proc.returncode == 0


def _git_merge_base(repo_root: Path, ref_a: str, ref_b: str = "HEAD") -> str | None:
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", ref_a, ref_b],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _git_lines(repo_root: Path, *args: str) -> list[str] | None:
    """Stripped non-empty stdout lines of ``git <args>``; None on any error."""
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _git_no_diff(repo_root: Path, *args: str) -> bool:
    """True only when ``git diff --quiet <args>`` reports no difference."""
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--quiet", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return proc.returncode == 0
