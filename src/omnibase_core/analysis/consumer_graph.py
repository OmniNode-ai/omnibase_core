# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Consumer graph builder: counts how many files import each module."""

import json
import subprocess
from pathlib import Path

from omnibase_core.analysis.import_graph import build_import_graph


def build_consumer_graph(repo_root: Path) -> dict[str, int]:
    """Return a mapping of repo-relative file path -> number of files that import it.

    Results are cached in .onex_state/consumer-graph.json keyed by the current
    git HEAD SHA. A SHA mismatch triggers a full recompute and cache overwrite.
    """
    repo_root = repo_root.resolve()
    cache_path = repo_root / ".onex_state" / "consumer-graph.json"
    head_sha = _git_head_sha(repo_root)

    if head_sha and cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(cached, dict) and cached.get("sha") == head_sha:
                return {
                    k: v
                    for k, v in cached.items()
                    if k != "sha" and isinstance(k, str) and isinstance(v, int)
                }
        except (json.JSONDecodeError, OSError):
            # Cache reads are best-effort; invalid or unreadable cache forces recompute.
            counts = _compute(repo_root)
            _write_cache(cache_path, head_sha, counts)
            return counts

    counts = _compute(repo_root)
    _write_cache(cache_path, head_sha, counts)
    return counts


def _compute(repo_root: Path) -> dict[str, int]:
    graph = build_import_graph(repo_root)
    counts: dict[str, int] = {}
    for _src, targets in graph.edges_out.items():
        for target in targets:
            counts[target] = counts.get(target, 0) + 1
    return counts


def _git_head_sha(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _write_cache(cache_path: Path, sha: str | None, counts: dict[str, int]) -> None:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {"sha": sha, **counts}
        cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        # Cache writes are best-effort; callers already have the computed graph.
        return
