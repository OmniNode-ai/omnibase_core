# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import json
import os
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import pytest

from omnibase_core.analysis import consumer_graph as consumer_graph_module
from omnibase_core.analysis.consumer_graph import build_consumer_graph
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

_REPO_SRC = str(Path(__file__).resolve().parents[2] / "src")


@pytest.mark.unit
def test_build_consumer_graph_counts_imports(tmp_path: Path) -> None:
    # a.py imports b.py; c.py imports b.py — b should have count 2
    (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("", encoding="utf-8")
    (tmp_path / "c.py").write_text("import b\n", encoding="utf-8")

    result = build_consumer_graph(tmp_path)

    assert "b.py" in result
    assert result["b.py"] == 2


@pytest.mark.unit
def test_build_consumer_graph_unreferenced_file_absent(tmp_path: Path) -> None:
    (tmp_path / "standalone.py").write_text("x = 1\n", encoding="utf-8")

    result = build_consumer_graph(tmp_path)

    assert "standalone.py" not in result


@pytest.mark.unit
def test_build_consumer_graph_cache_hit(tmp_path: Path) -> None:
    (tmp_path / "x.py").write_text("import y\n", encoding="utf-8")
    (tmp_path / "y.py").write_text("", encoding="utf-8")

    # Prime cache by calling once (no git repo, sha=None)
    build_consumer_graph(tmp_path)

    cache_path = tmp_path / ".onex_state" / "consumer-graph.json"
    assert cache_path.is_file()

    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    assert "y.py" in cached


@pytest.mark.unit
def test_build_consumer_graph_sha_mismatch_recomputes(tmp_path: Path) -> None:
    # Write a stale cache with a known SHA
    cache_path = tmp_path / ".onex_state" / "consumer-graph.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    stale = {"sha": "deadbeef" * 5, "old_file.py": 99}
    cache_path.write_text(json.dumps(stale), encoding="utf-8")

    (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("", encoding="utf-8")

    result = build_consumer_graph(tmp_path)

    # old stale entry must be gone; real computation used
    assert "old_file.py" not in result
    assert result.get("b.py") == 1


@pytest.mark.unit
def test_build_consumer_graph_returns_dict_str_int(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("import util\n", encoding="utf-8")
    (tmp_path / "util.py").write_text("", encoding="utf-8")

    result = build_consumer_graph(tmp_path)

    assert isinstance(result, dict)
    for k, v in result.items():
        assert isinstance(k, str)
        assert isinstance(v, int)


def _git(repo: Path, *args: str) -> None:
    """Run one git command in repo with the location overrides scrubbed.

    GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE are exported into every hook process
    and override both cwd= and -C, so an unscrubbed call here would retarget the
    real invoking worktree instead of repo (OMN-14891).
    """
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        env={
            **scrub_git_location_env(os.environ),
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )


def _init_git_repo(path: Path) -> None:
    """Make path a real git repo so build_consumer_graph resolves a HEAD SHA.

    The SHA is the cache key: without one the cache is never reused, so any
    test about cache/lock behaviour must run against a genuine repo.
    """
    _git(path, "init", "-q")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "seed", "--no-gpg-sign")


@pytest.mark.unit
def test_vendored_dependency_dirs_are_not_counted_as_consumers(tmp_path: Path) -> None:
    """Vendored trees must not be walked (OMN-15431).

    Walking .venv both inflated cold-build cost into the per-test timeout and
    corrupted the counts: a site-packages copy of a first-party module is a
    different file than the real src/ one.
    """
    (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("", encoding="utf-8")

    vendored = tmp_path / ".venv" / "lib" / "python3.12" / "site-packages"
    vendored.mkdir(parents=True)
    (vendored / "vendor_consumer.py").write_text("import b\n", encoding="utf-8")

    result = build_consumer_graph(tmp_path)

    # Only the first-party importer counts; the vendored one is invisible.
    assert result["b.py"] == 1
    assert not any(key.startswith(".venv/") for key in result)


@pytest.mark.unit
def test_nested_checkout_is_not_counted_as_consumers(tmp_path: Path) -> None:
    """A nested checkout (worktree/submodule) is not this repo's source."""
    (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("", encoding="utf-8")

    nested = tmp_path / "nested_repo"
    (nested / ".git").mkdir(parents=True)
    (nested / "nested_consumer.py").write_text("import b\n", encoding="utf-8")

    result = build_consumer_graph(tmp_path)

    assert result["b.py"] == 1
    assert not any(key.startswith("nested_repo/") for key in result)


_CONCURRENT_BUILD_WORKER = """
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, "@SRC@")
from omnibase_core.analysis import consumer_graph

started_dir = Path("@STARTED@")
computed_log = Path("@COMPUTED@")
real_compute = consumer_graph._compute


def instrumented(repo_root):
    with computed_log.open("a", encoding="utf-8") as handle:
        handle.write("build\\n")
    time.sleep(@BUILD_SECONDS@)
    return real_compute(repo_root)


consumer_graph._compute = instrumented

# Rendezvous: hold every worker until all of them are past interpreter startup.
# Without this a fast first worker could finish and warm the cache before the
# others even start, and the test would pass with no single-flight lock at all.
(started_dir / str(os.getpid())).write_text("1", encoding="utf-8")
deadline = time.monotonic() + 30.0
while len(list(started_dir.iterdir())) < @WORKERS@ and time.monotonic() < deadline:
    time.sleep(0.01)

consumer_graph.build_consumer_graph(Path("@REPO@"))
"""


@pytest.mark.unit
def test_concurrent_cold_builds_compute_the_graph_exactly_once(
    tmp_path: Path,
) -> None:
    """Single-flight: N cold processes produce ONE build, not N (OMN-15431).

    This is the defect that crashed the suite: four xdist workers each ran a
    full-repo consumer-graph build at the same time, so every one of them
    exceeded the 60s per-test timeout and xdist died with a scheduler KeyError.
    """
    workers = 4
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("import b\n", encoding="utf-8")
    (repo / "b.py").write_text("", encoding="utf-8")
    _init_git_repo(repo)

    started_dir = tmp_path / "started"
    started_dir.mkdir()
    computed_log = tmp_path / "computed.log"

    script = (
        _CONCURRENT_BUILD_WORKER.replace("@SRC@", _REPO_SRC)
        .replace("@REPO@", str(repo))
        .replace("@STARTED@", str(started_dir))
        .replace("@COMPUTED@", str(computed_log))
        .replace("@BUILD_SECONDS@", "1.0")
        .replace("@WORKERS@", str(workers))
    )

    procs = [
        subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(workers)
    ]
    for proc in procs:
        _, stderr = proc.communicate(timeout=120)
        assert proc.returncode == 0, f"worker failed: {stderr}"

    builds = computed_log.read_text(encoding="utf-8").split()
    assert len(builds) == 1, f"expected exactly one build, got {len(builds)}"

    # The published cache is intact and no temp file leaked from the atomic swap.
    cache_path = repo / ".onex_state" / "consumer-graph.json"
    assert json.loads(cache_path.read_text(encoding="utf-8"))["b.py"] == 1
    assert not list(cache_path.parent.glob("*.tmp"))


@pytest.mark.unit
def test_failed_cache_write_leaves_the_previous_cache_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Atomic publish: a write that dies mid-flight must not truncate the cache.

    A plain write() truncates the destination first, so a reader concurrent with
    a failing writer sees a torn file and falls back to a redundant full rebuild.
    """
    cache_path = tmp_path / ".onex_state" / "consumer-graph.json"
    cache_path.parent.mkdir(parents=True)
    previous = {"sha": "cafebabe" * 5, "kept.py": 7}
    cache_path.write_text(json.dumps(previous), encoding="utf-8")

    def explode(_fd: int) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(consumer_graph_module.os, "fsync", explode)

    consumer_graph_module._write_cache(cache_path, "f" * 40, {"new.py": 1})

    # Destination still holds the prior graph, byte for byte, and no temp leaked.
    assert json.loads(cache_path.read_text(encoding="utf-8")) == previous
    assert not list(cache_path.parent.glob("*.tmp"))


@pytest.mark.unit
def test_build_still_completes_when_the_lock_cannot_be_taken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lock is a stampede guard, never a correctness barrier.

    If it cannot be acquired the build must still produce a correct graph rather
    than wedge -- a lock that can hang is worse than the timeout it prevents.
    """
    (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("", encoding="utf-8")

    monkeypatch.setattr(consumer_graph_module, "_HAVE_FCNTL", False)

    started = time.monotonic()
    result = build_consumer_graph(tmp_path)

    assert result["b.py"] == 1
    assert time.monotonic() - started < 60.0


@pytest.mark.unit
def test_lock_wait_never_outlasts_the_gate_per_test_timeout() -> None:
    """A waiter must not block past the budget that will kill it anyway.

    The single-flight lock turns N-1 concurrent cold builders into N-1 waiters.
    pytest-timeout kills each of them at the ``--timeout=`` pinned in pyproject
    addopts, so a wait longer than that budget cannot rescue a waiter -- it only
    keeps an already-doomed process holding an xdist worker slot, which is the
    exact OMN-15431 failure shape. This pins the lock wait against the real
    gate value rather than a number copied into a comment.
    """
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject.open("rb") as handle:
        addopts = tomllib.load(handle)["tool"]["pytest"]["ini_options"]["addopts"]

    timeouts = [
        float(opt.split("=", 1)[1]) for opt in addopts if opt.startswith("--timeout=")
    ]
    assert timeouts, f"no --timeout= in pyproject addopts: {addopts}"

    assert min(timeouts) >= consumer_graph_module._LOCK_TIMEOUT_SECONDS, (
        f"lock wait {consumer_graph_module._LOCK_TIMEOUT_SECONDS}s exceeds the "
        f"gate per-test timeout {min(timeouts)}s; waiters would be killed mid-wait"
    )
