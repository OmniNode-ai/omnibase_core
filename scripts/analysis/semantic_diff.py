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


def _git_file_at(ref: str, rel_path: str, repo_root: Path) -> str:
    """Return file content at given ref, empty string if not present."""
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{rel_path}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def _compute_report(base: str, head: str, repo_root: Path) -> ModelSemanticDiffReport:
    consumer_graph = build_consumer_graph(repo_root)
    changed_files = _git_changed_py_files(base, head, repo_root)

    all_changes: list[ModelSymbolChange] = []
    total_consumers = 0

    for file_path in changed_files:
        rel = file_path.relative_to(repo_root).as_posix()
        old_source = _git_file_at(base, rel, repo_root)
        new_source = _git_file_at(head, rel, repo_root)
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
