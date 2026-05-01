# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import json
import re
import threading
from collections import deque
from pathlib import Path

from omnibase_core.models.agents.model_trajectory_entry import ModelTrajectoryEntry

_CACHE_CAP = 1000
_EVICT_COUNT = 500
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _validate_session_id(session_id: str) -> str:
    if not isinstance(session_id, str):
        # error-ok: typed local validation rejects non-string session IDs
        raise TypeError(f"session_id must be a string, got {type(session_id).__name__}")

    normalized = session_id.strip()
    if not _SESSION_ID_PATTERN.fullmatch(normalized):
        # error-ok: local validation rejects path-unsafe session IDs
        raise ValueError(
            "session_id must contain only letters, numbers, dots, underscores, "
            "or hyphens, and must start with a letter or number"
        )
    if ".." in normalized:
        # error-ok: local validation rejects path traversal segments
        raise ValueError("session_id must not contain path traversal segments")
    return normalized


class TrajectoryStore:
    """JSONL-backed trajectory store with a bounded in-memory cache."""

    def __init__(self, session_id: str, state_dir: Path | None = None) -> None:
        self._session_id = _validate_session_id(session_id)
        root = state_dir if state_dir is not None else Path(".onex_state")
        self._jsonl_path = root / "trajectory" / f"{self._session_id}.jsonl"
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
        if n < 0:
            # error-ok: CodeRabbit review requires ValueError for negative n
            raise ValueError("n must be greater than or equal to 0")
        if n == 0:
            return []

        with self._lock:
            items = list(self._cache)
        return items[-n:] if n < len(items) else items
