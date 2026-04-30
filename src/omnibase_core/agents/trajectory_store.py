# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import json
import threading
from collections import deque
from pathlib import Path

from omnibase_core.models.agents.model_trajectory_entry import ModelTrajectoryEntry

_CACHE_CAP = 1000
_EVICT_COUNT = 500


class TrajectoryStore:
    """JSONL-backed trajectory store with a bounded in-memory cache."""

    def __init__(self, session_id: str, state_dir: Path | None = None) -> None:
        self._session_id = session_id
        root = state_dir if state_dir is not None else Path(".onex_state")
        self._jsonl_path = root / "trajectory" / f"{session_id}.jsonl"
        self._jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: deque[ModelTrajectoryEntry] = deque()
        self._lock = threading.Lock()

    def append(self, entry: ModelTrajectoryEntry) -> None:
        with self._lock:
            line = json.dumps(entry.model_dump(mode="json")) + "\n"
            with self._jsonl_path.open("a", encoding="utf-8") as fh:
                fh.write(line)
            self._cache.append(entry)
            if len(self._cache) > _CACHE_CAP:
                for _ in range(_EVICT_COUNT):
                    self._cache.popleft()

    def read_recent(self, n: int) -> list[ModelTrajectoryEntry]:
        with self._lock:
            items = list(self._cache)
        return items[-n:] if n < len(items) else items
