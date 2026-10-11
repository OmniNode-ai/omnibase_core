# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""SQLite-backed deduplication store for the Linear relay service.

Schema: (key TEXT PRIMARY KEY, created_at REAL)
Cleans entries older than 24 hours on each insert.
SQLite handles concurrency natively — no file locks needed.

See OMN-3502 for specification.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

# Default database path — can be overridden in tests
_DEFAULT_DB_PATH = Path("/tmp/linear_relay_dedup.db")  # noqa: S108  # nosec B108

# Entries older than this are removed on insert
_TTL_SECONDS = 86400  # 24 hours


class DedupStore:
    """SQLite-backed deduplication store.

    Thread-safe via SQLite's built-in concurrency handling.
    Each instance opens its own connection.

    Args:
        db_path: Path to the SQLite database file.
            Defaults to ``/tmp/linear_relay_dedup.db``.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _DEFAULT_DB_PATH
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        """Create the dedup table if it does not exist."""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dedup (
                key        TEXT    PRIMARY KEY,
                created_at REAL    NOT NULL
            )
            """
        )
        self._conn.commit()

    def is_duplicate(self, key: str) -> bool:
        """Check if a key is a duplicate and record it if not.

        Cleans entries older than 24 hours before checking.

        Args:
            key: Deduplication key (e.g. webhookId).

        Returns:
            ``True`` if the key was already present (duplicate),
            ``False`` if the key was new (just recorded).
        """
        now = time.time()
        cutoff = now - _TTL_SECONDS

        # Clean stale entries before inserting
        self._conn.execute("DELETE FROM dedup WHERE created_at < ?", (cutoff,))

        try:
            self._conn.execute(
                "INSERT INTO dedup (key, created_at) VALUES (?, ?)",
                (key, now),
            )
            self._conn.commit()
            return False
        except sqlite3.IntegrityError:
            # PRIMARY KEY conflict: key already exists
            self._conn.rollback()
            return True

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()
