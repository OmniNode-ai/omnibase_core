# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import json
import threading
from pathlib import Path

import pytest

from omnibase_core.agents.trajectory_store import TrajectoryStore
from omnibase_core.models.agents.model_trajectory_entry import ModelTrajectoryEntry


def _make_entry(step: int) -> ModelTrajectoryEntry:
    return ModelTrajectoryEntry(
        step=step,
        agent="agent-a",
        action="edit",
        target="src/foo.py",
        result="ok",
    )


@pytest.mark.unit
def test_append_writes_jsonl_line(tmp_path: Path) -> None:
    store = TrajectoryStore(session_id="sess-1", state_dir=tmp_path)
    entry = _make_entry(1)
    store.append(entry)

    jsonl_path = tmp_path / "trajectory" / "sess-1.jsonl"
    assert jsonl_path.exists()
    lines = jsonl_path.read_text().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["step"] == 1
    assert parsed["agent"] == "agent-a"


@pytest.mark.unit
@pytest.mark.parametrize(
    "session_id",
    [
        "../escape",
        "nested/session",
        "nested\\session",
        "sess..escape",
        ".hidden",
        "",
    ],
)
def test_session_id_rejects_path_unsafe_values(tmp_path: Path, session_id: str) -> None:
    with pytest.raises(ValueError):
        TrajectoryStore(session_id=session_id, state_dir=tmp_path)


@pytest.mark.unit
def test_append_multiple_entries_each_on_own_line(tmp_path: Path) -> None:
    store = TrajectoryStore(session_id="sess-2", state_dir=tmp_path)
    for i in range(5):
        store.append(_make_entry(i))

    jsonl_path = tmp_path / "trajectory" / "sess-2.jsonl"
    lines = jsonl_path.read_text().splitlines()
    assert len(lines) == 5
    for i, line in enumerate(lines):
        assert json.loads(line)["step"] == i


@pytest.mark.unit
def test_cache_bounded_at_1000_drops_oldest_500(tmp_path: Path) -> None:
    store = TrajectoryStore(session_id="sess-3", state_dir=tmp_path)
    for i in range(1001):
        store.append(_make_entry(i))

    # cache should have 501 entries (1001 - 500 dropped)
    cache = store.read_recent(2000)
    assert len(cache) == 501
    # oldest in cache should be step 500 (steps 0-499 were dropped)
    assert cache[0].step == 500
    # file is unbounded — all 1001 lines
    jsonl_path = tmp_path / "trajectory" / "sess-3.jsonl"
    assert len(jsonl_path.read_text().splitlines()) == 1001


@pytest.mark.unit
def test_read_recent_returns_newest_n(tmp_path: Path) -> None:
    store = TrajectoryStore(session_id="sess-4", state_dir=tmp_path)
    for i in range(10):
        store.append(_make_entry(i))

    recent = store.read_recent(3)
    assert len(recent) == 3
    # newest 3 are steps 7, 8, 9
    assert [e.step for e in recent] == [7, 8, 9]


@pytest.mark.unit
def test_read_recent_zero_returns_empty_list(tmp_path: Path) -> None:
    store = TrajectoryStore(session_id="sess-zero", state_dir=tmp_path)
    store.append(_make_entry(1))

    assert store.read_recent(0) == []


@pytest.mark.unit
def test_read_recent_negative_raises(tmp_path: Path) -> None:
    store = TrajectoryStore(session_id="sess-negative", state_dir=tmp_path)

    with pytest.raises(ValueError, match="greater than or equal to 0"):
        store.read_recent(-1)


@pytest.mark.unit
def test_read_recent_fewer_than_n_returns_all(tmp_path: Path) -> None:
    store = TrajectoryStore(session_id="sess-5", state_dir=tmp_path)
    for i in range(3):
        store.append(_make_entry(i))

    recent = store.read_recent(10)
    assert len(recent) == 3


@pytest.mark.unit
def test_concurrent_appends_serialised(tmp_path: Path) -> None:
    store = TrajectoryStore(session_id="sess-6", state_dir=tmp_path)
    n_threads = 20
    entries_per_thread = 50

    def worker(offset: int) -> None:
        for i in range(entries_per_thread):
            store.append(_make_entry(offset + i))

    threads = [
        threading.Thread(target=worker, args=(t * entries_per_thread,))
        for t in range(n_threads)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    jsonl_path = tmp_path / "trajectory" / "sess-6.jsonl"
    lines = jsonl_path.read_text().splitlines()
    assert len(lines) == n_threads * entries_per_thread
    # every line must be valid JSON
    for line in lines:
        obj = json.loads(line)
        assert "step" in obj
