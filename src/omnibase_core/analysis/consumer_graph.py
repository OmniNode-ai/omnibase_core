# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Consumer graph builder: counts how many files import each module."""

import json
import os
import subprocess
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

from omnibase_core.analysis.import_graph import build_import_graph

try:  # pragma: no cover - POSIX always provides fcntl
    import fcntl

    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX fallback
    _HAVE_FCNTL = False

_LOCK_POLL_SECONDS = 0.05

# The canonical gate pins --timeout=60 (pyproject.toml [tool.pytest.ini_options]
# addopts), so a waiter that blocks past 60s is killed by pytest-timeout anyway.
# Waiting longer cannot rescue it -- it only keeps a doomed process holding an
# xdist worker slot. The wait therefore never exceeds the tightest per-test
# budget this lock is documented against (OMN-15431).
_LOCK_TIMEOUT_SECONDS = 60.0


def build_consumer_graph(repo_root: Path) -> dict[str, int]:
    """Return a mapping of repo-relative file path -> number of files that import it.

    Results are cached in .onex_state/consumer-graph.json keyed by the current
    git HEAD SHA. A SHA mismatch triggers a full recompute and cache overwrite.

    Concurrent callers are single-flighted through an inter-process lock: when
    several processes hit a cold cache at once, exactly one computes the graph
    and the rest wait and then read its result. Without that, N concurrent test
    workers each ran a full-repo build simultaneously (OMN-15431).

    Read the division of labour precisely, because the lock alone is NOT a fix
    for the timeout class: it collapses N concurrent builds into one, removing
    the CPU/IO contention that made every one of them slower, but it converts
    N-1 builders into N-1 waiters. What bounds the latency of the single
    remaining build -- and so of everyone waiting on it -- is the pruned tree
    walk in ``build_import_graph``. If that build ever regresses past the gate's
    per-test budget again, the waiters die with it.
    """
    repo_root = repo_root.resolve()
    state_dir = repo_root / ".onex_state"
    cache_path = state_dir / "consumer-graph.json"
    head_sha = _git_head_sha(repo_root)

    cached = _read_cache(cache_path, head_sha)
    if cached is not None:
        return cached

    with _single_flight_lock(state_dir / "consumer-graph.lock") as holding_lock:
        if holding_lock:
            # Double-checked: whoever held the lock before us may have already
            # built and published exactly the graph we are about to compute.
            cached = _read_cache(cache_path, head_sha)
            if cached is not None:
                return cached
        counts = _compute(repo_root)
        _write_cache(cache_path, head_sha, counts)
        return counts


@contextmanager
def _single_flight_lock(lock_path: Path) -> Iterator[bool]:
    """Best-effort exclusive inter-process lock around a cold graph build.

    Yields True while the lock is held and False when it could not be taken
    (no fcntl, unwritable state dir, or timeout). The lock collapses a stampede
    into one build; it is never a correctness barrier, so a False yield must
    still let the caller compute its own result rather than wedge the build.
    """
    if not _HAVE_FCNTL:
        yield False
        return

    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("w", encoding="utf-8")
    except OSError:
        yield False
        return

    acquired = False
    deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
    try:
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError:
                if time.monotonic() >= deadline:
                    break
                time.sleep(_LOCK_POLL_SECONDS)
        yield acquired
    finally:
        if acquired:
            with suppress(OSError):
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _read_cache(cache_path: Path, head_sha: str | None) -> dict[str, int] | None:
    """Return cached counts for head_sha, or None if absent, stale, or unreadable."""
    if not head_sha:
        return None
    try:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Cache reads are best-effort; an invalid or unreadable cache forces recompute.
        return None
    if not isinstance(cached, dict) or cached.get("sha") != head_sha:
        return None
    return {
        k: v
        for k, v in cached.items()
        if k != "sha" and isinstance(k, str) and isinstance(v, int)
    }


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
    """Publish the cache atomically (temp file + os.replace).

    A plain write leaves the destination truncated mid-update, so a concurrent
    reader can observe a torn, unparseable graph and fall back to a redundant
    full rebuild. os.replace makes the swap atomic: readers see either the
    previous graph or the new one, never a partial one.
    """
    payload: dict[str, object] = {"sha": sha, **counts}
    tmp_path: Path | None = None
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=cache_path.parent,
            prefix=f"{cache_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            json.dump(payload, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.replace(cache_path)
    except OSError:
        # Cache writes are best-effort; callers already have the computed graph.
        if tmp_path is not None:
            with suppress(OSError):
                tmp_path.unlink()
