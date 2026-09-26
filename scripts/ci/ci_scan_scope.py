# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Decide which tracked files a per-file CI validator scans (OMN-19614).

Detect Secrets and AI Slop Patterns check one file at a time, so on a pull
request it is enough to scan the files the pull request changes: two pull
requests that are each clean on their own diff cannot combine into a violation
of a per-file rule. Everything else scans the whole tracked tree.

The full tree is scanned when ANY of these holds:

* the event is not ``pull_request`` (push, merge_group, schedule and
  workflow_dispatch always scan everything, which is what keeps the whole tree
  covered on ``dev`` and nightly);
* the pull request's base cannot be resolved. On ``pull_request`` the checkout
  is GitHub's synthetic merge commit, whose first parent is the base tip and
  whose second parent is the pull request head. If HEAD is not a two-parent
  commit, or its second parent is not the head sha the event names, the diff is
  not trusted and the scan falls back to the full tree (fail closed);
* a changed path (added, modified, renamed from or to, or deleted) matches a
  ``--force-full`` pattern. Callers list the validator, its config, its
  baseline and the workflow that pins its version, because a change to any of
  those can change the verdict on files the pull request did not touch.

Stdlib only: the Detect Secrets job runs it before any project environment
exists.

Usage::

    python3 scripts/ci/ci_scan_scope.py --event pull_request \
        --pr-head-sha <sha> --force-full .secrets.baseline \
        --nul --out scan-files.bin

Exit codes: 0 when a scope was decided and written, 2 on a usage error or when
``git ls-files`` itself fails (nothing can be scanned, so the caller must fail).
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

MODE_FULL = "full"
MODE_DIFF = "diff"


@dataclass(frozen=True)
class ScanScope:
    """The files to scan and why."""

    mode: str
    reason: str
    files: tuple[str, ...]


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # fixed git argv, no shell
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        check=False,
    )


def _split_nul(raw: bytes) -> list[str]:
    return [item.decode() for item in raw.split(b"\0") if item]


def tracked_files(repo: Path) -> list[str]:
    """Every tracked path, or raise when git cannot list them."""
    result = _git(["ls-files", "-z"], repo)
    if result.returncode != 0:
        raise RuntimeError(
            f"git ls-files failed: {result.stderr.decode(errors='replace').strip()}"
        )
    return _split_nul(result.stdout)


def _resolve_pr_base(repo: Path, pr_head_sha: str) -> tuple[str | None, str]:
    """Return ``(base_sha, reason)``; ``base_sha`` is None when unresolvable."""
    if not pr_head_sha:
        return None, "no pull request head sha was given"
    parents = _git(["rev-list", "--parents", "-n", "1", "HEAD"], repo)
    if parents.returncode != 0:
        return None, "HEAD could not be read"
    shas = parents.stdout.decode().split()
    if len(shas) != 3:
        return None, (
            f"HEAD has {len(shas) - 1} parent(s), not the two of a pull request "
            "merge commit"
        )
    _head, base_sha, merged_head = shas
    if merged_head != pr_head_sha:
        return None, (
            f"HEAD's second parent {merged_head[:12]} is not the pull request "
            f"head {pr_head_sha[:12]}"
        )
    return base_sha, f"base {base_sha[:12]} (first parent of the merge commit)"


def _changed_paths(repo: Path, base_sha: str) -> tuple[list[str], list[str]] | None:
    """Return ``(scannable, touched)`` or None when git cannot diff.

    ``scannable`` is what exists at HEAD (added, copied, modified, renamed to,
    type changed). ``touched`` is every path the diff names on either side,
    deletions and rename sources included, for the force-full check.
    """
    scannable = _git(
        [
            "diff",
            "--name-only",
            "-z",
            "--no-renames",
            "--diff-filter=ACMRT",
            base_sha,
            "HEAD",
        ],
        repo,
    )
    touched = _git(
        ["diff", "--name-only", "-z", "--no-renames", base_sha, "HEAD"], repo
    )
    if scannable.returncode != 0 or touched.returncode != 0:
        return None
    return _split_nul(scannable.stdout), _split_nul(touched.stdout)


def decide_scope(
    *,
    repo: Path,
    event: str,
    pr_head_sha: str,
    force_full: list[str],
) -> ScanScope:
    """Decide the scan scope. Every uncertain branch resolves to the full tree."""
    all_files = tracked_files(repo)

    def full(reason: str) -> ScanScope:
        return ScanScope(mode=MODE_FULL, reason=reason, files=tuple(all_files))

    if event != "pull_request":
        return full(f"event is {event or '<empty>'}, not pull_request")

    base_sha, base_reason = _resolve_pr_base(repo, pr_head_sha)
    if base_sha is None:
        return full(f"pull request base unresolvable: {base_reason}")

    changed = _changed_paths(repo, base_sha)
    if changed is None:
        return full(f"git diff against {base_sha[:12]} failed")
    scannable, touched = changed

    for path in touched:
        for pattern in force_full:
            if fnmatch.fnmatchcase(path, pattern):
                return full(f"{path} changed and matches force-full pattern {pattern}")

    tracked = set(all_files)
    files = tuple(path for path in scannable if path in tracked)
    return ScanScope(
        mode=MODE_DIFF,
        reason=f"pull request diff against {base_reason}",
        files=files,
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", required=True, help="github.event_name")
    parser.add_argument(
        "--pr-head-sha",
        default="",
        help="github.event.pull_request.head.sha (empty outside pull_request)",
    )
    parser.add_argument(
        "--force-full",
        action="append",
        default=[],
        metavar="GLOB",
        help="a changed path matching this fnmatch pattern forces the full tree",
    )
    parser.add_argument("--out", required=True, type=Path, help="file list to write")
    parser.add_argument(
        "--nul", action="store_true", help="NUL-separate the list (default newline)"
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        scope = decide_scope(
            repo=args.repo,
            event=args.event,
            pr_head_sha=args.pr_head_sha,
            force_full=list(args.force_full),
        )
    except RuntimeError as exc:
        sys.stderr.write(f"ci_scan_scope: {exc}\n")
        return 2

    separator = "\0" if args.nul else "\n"
    body = separator.join(scope.files)
    if scope.files:
        body += separator
    args.out.write_text(body, encoding="utf-8")

    sys.stdout.write(f"scan scope: mode={scope.mode} files={len(scope.files)}\n")
    sys.stdout.write(f"reason: {scope.reason}\n")
    if scope.mode == MODE_DIFF:
        for path in scope.files:
            sys.stdout.write(f"  {path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
