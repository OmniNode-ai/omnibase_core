#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI: compute AST-level semantic diff between two git refs (OMN-10375).

Usage:
    python scripts/analysis/semantic_diff.py --base origin/main --head HEAD --json

Exits 0 on completed analysis; argparse usage errors still exit non-zero.
Detected changes are advisory. Gating is opt-in via separate workflows.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from omnibase_core.analysis.consumer_graph import build_consumer_graph
from omnibase_core.analysis.semantic_diff import compute_diff
from omnibase_core.models.analysis.model_semantic_diff_report import (
    ModelSemanticDiffReport,
)
from omnibase_core.models.analysis.model_symbol_change import ModelSymbolChange


def _git_ref_exists(ref: str, repo_root: Path) -> bool:
    return (
        subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        == 0
    )


def _ensure_ref_available(ref: str, repo_root: Path) -> bool:
    if _git_ref_exists(ref, repo_root):
        return True

    if ref.startswith("origin/"):
        branch = ref.removeprefix("origin/")
        subprocess.run(
            [
                "git",
                "fetch",
                "--depth=1",
                "origin",
                f"refs/heads/{branch}:refs/remotes/origin/{branch}",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

    return _git_ref_exists(ref, repo_root)


def _git_changed_py_files(base: str, head: str, repo_root: Path) -> list[Path]:
    if not _ensure_ref_available(base, repo_root):
        print(  # noqa: T201
            f"warning: base ref {base!r} is unavailable; emitting empty advisory report",
            file=sys.stderr,
        )
        return []
    if not _ensure_ref_available(head, repo_root):
        print(  # noqa: T201
            f"warning: head ref {head!r} is unavailable; emitting empty advisory report",
            file=sys.stderr,
        )
        return []

    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMDR",
            f"{base}...{head}",
            "--",
            "*.py",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(  # noqa: T201
            "warning: git diff failed for "
            f"{base!r}...{head!r}: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return []
    return [repo_root / line for line in result.stdout.splitlines() if line]


def _git_files_at(
    repo_root: Path, requests: list[tuple[str, str]]
) -> dict[tuple[str, str], str]:
    """Read every requested ``<ref>:<path>`` blob in ONE git process.

    The previous shape spawned two ``git show`` processes per changed file, so a
    1,000-file diff paid ~2,000 process spawns and that dominated CLI runtime --
    enough, under the parallel test gate, to push the run past its per-test
    timeout. ``git cat-file --batch`` answers the whole set from a single
    process. Missing blobs yield "", matching the previous per-file behaviour.
    See OMN-15431.
    """
    if not requests:
        return {}

    payload = "".join(f"{ref}:{rel}\n" for ref, rel in requests).encode()
    result = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=repo_root,
        input=payload,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return {}

    out = result.stdout
    sources: dict[tuple[str, str], str] = {}
    pos = 0
    for key in requests:
        end_of_header = out.find(b"\n", pos)
        if end_of_header == -1:
            break
        header = out[pos:end_of_header]
        pos = end_of_header + 1
        # Success is "<oid> <type> <size>"; absence is "<request> missing".
        fields = header.split(b" ")
        try:
            size = int(fields[2])
        except (IndexError, ValueError):
            sources[key] = ""
            continue
        sources[key] = out[pos : pos + size].decode("utf-8", errors="replace")
        pos += size + 1  # blob payload plus its trailing newline

    return sources


def _compute_report(base: str, head: str, repo_root: Path) -> ModelSemanticDiffReport:
    changed_files = _git_changed_py_files(base, head, repo_root)
    if not changed_files:
        return ModelSemanticDiffReport(
            changes=(),
            total_consumers_affected=0,
        )

    consumer_graph = build_consumer_graph(repo_root)

    all_changes: list[ModelSymbolChange] = []
    total_consumers = 0

    rel_paths = [
        file_path.relative_to(repo_root).as_posix() for file_path in changed_files
    ]
    sources = _git_files_at(
        repo_root,
        [(ref, rel) for rel in rel_paths for ref in (base, head)],
    )

    for rel in rel_paths:
        old_source = sources.get((base, rel), "")
        new_source = sources.get((head, rel), "")
        consumers = consumer_graph.get(rel, 0)
        report = compute_diff(old_source, new_source, rel, consumers)
        all_changes.extend(report.changes)
        if report.changes:
            total_consumers += consumers

    return ModelSemanticDiffReport(
        changes=tuple(all_changes),
        total_consumers_affected=total_consumers,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AST semantic diff between two git refs"
    )
    parser.add_argument("--base", required=True, help="Base git ref (e.g. origin/main)")
    parser.add_argument("--head", required=True, help="Head git ref (e.g. HEAD)")
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON report to stdout"
    )
    args = parser.parse_args()

    report = _compute_report(args.base, args.head, _REPO_ROOT)

    if args.json:
        print(json.dumps(report.model_dump(), indent=2))  # noqa: T201
    elif not report.changes:
        print("No semantic changes detected.")  # noqa: T201
    else:
        for change in report.changes:
            print(  # noqa: T201
                f"[{change.severity.upper()}] {change.kind}: {change.symbol_name} ({change.file_path})"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
