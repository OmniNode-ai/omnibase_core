# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI: co-change dark matter analysis.

Usage:
    python scripts/analysis/co_change_dark_matter.py          # human-readable top 20
    python scripts/analysis/co_change_dark_matter.py --json   # JSON to stdout
    python scripts/analysis/co_change_dark_matter.py --write-state  # write to .onex_state/
"""

from __future__ import annotations

import sys
from pathlib import Path

# Insert the worktree src at position 0 so local (possibly uncommitted) modules
# take priority over any installed version of the package. This is necessary
# when running from a stacked worktree where analysis/ is not yet installed.
_SCRIPT_SRC = Path(__file__).resolve().parents[2] / "src"
if _SCRIPT_SRC.is_dir():
    _src_str = str(_SCRIPT_SRC)
    # Always insert at 0: PYTHONPATH may have placed a different (canonical)
    # src earlier, which would shadow the worktree's local modules.
    if sys.path and sys.path[0] != _src_str:
        sys.path.insert(0, _src_str)

import json
import subprocess

from omnibase_core.types.typed_dict_dark_matter_pair import TypedDictDarkMatterPair


def _git_commits(repo_root: Path) -> list[list[str]]:
    """Return per-commit file lists from git log."""
    try:
        out = subprocess.check_output(
            ["git", "log", "--name-only", "--pretty=format:---COMMIT---"],
            cwd=str(repo_root),
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    commits: list[list[str]] = []
    current: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if line == "---COMMIT---":
            if current:
                commits.append(current)
            current = []
        elif line:
            current.append(line)
    if current:
        commits.append(current)
    return commits


def _find_repo_root(start: Path) -> Path:
    """Walk up to find the git root, or return start if not found."""
    current = start.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return current


def _analyse(repo_root: Path) -> list[TypedDictDarkMatterPair]:
    """Build matrix, import graph, and run dark matter filter."""
    from omnibase_core.analysis.co_change_dark_matter import find_dark_matter
    from omnibase_core.analysis.co_change_matrix import build_cochange_matrix
    from omnibase_core.analysis.import_graph import build_import_graph

    commits = _git_commits(repo_root)
    matrix = build_cochange_matrix(commits)
    import_graph = build_import_graph(repo_root)
    return find_dark_matter(matrix, import_graph)


def main() -> int:
    args = sys.argv[1:]
    cwd = Path.cwd()
    repo_root = _find_repo_root(cwd)

    pairs = _analyse(repo_root)

    if "--json" in args:
        print(json.dumps({"pairs": list(pairs)}, indent=2))
        return 0

    if "--write-state" in args:
        state_dir = cwd / ".onex_state"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "co-change-map.json"
        state_file.write_text(json.dumps({"pairs": list(pairs)}, indent=2))
        return 0

    # Human-readable top 20
    if not pairs:
        print("No dark matter pairs found.")
        return 0

    print(f"{'NPMI':>6}  {'Co-changes':>10}  {'File A':<40}  {'File B'}")
    print("-" * 90)
    for p in pairs[:20]:
        print(f"{p['npmi']:>6.3f}  {p['co_changes']:>10}  {p['a']!s:<40}  {p['b']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
