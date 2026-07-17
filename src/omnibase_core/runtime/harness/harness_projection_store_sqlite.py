# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""SQLite projection store for the local runtime harness (OMN-13420).

Zero infra, zero LAN. Pass ``path=":memory:"`` (default) for fully ephemeral runs,
or a file path for a durable readback artifact.

Postgres-specific migration/view validation (CASCADE/JSONB/view migrations, the
A5/A7 class) is out of scope here — that remains the infra-backed broker proof.
This adapter proves the in-process command -> terminal -> projection chain only.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from uuid import UUID

from omnibase_core.models.runtime.harness.model_projection_row import ModelProjectionRow


class SqliteProjectionStore:
    """SQLite-backed projection store — zero infra, zero LAN.

    The schema is created on construction so a fresh DB is immediately usable.
    """

    _TABLE = "harness_projection"

    def __init__(self, path: str = ":memory:") -> None:
        self._path = path
        # check_same_thread=False so the single-process asyncio harness can reuse
        # the connection across the event-loop callback boundary.
        self._conn = sqlite3.connect(
            path, check_same_thread=False
        )  # di-ok: this IS the local-harness projection-store adapter bootstrap (zero-infra, in-process); it owns its own connection by design (OMN-13420)
        self._conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._TABLE} (
                correlation_id TEXT PRIMARY KEY,
                workflow TEXT NOT NULL,
                terminal_topic TEXT NOT NULL,
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    @property
    def path(self) -> str:
        """Return the SQLite database path (``:memory:`` for ephemeral)."""
        return self._path

    @property
    def backend(self) -> str:
        """Return a human-readable backend identifier for evidence packets."""
        return f"sqlite:{self._path}"

    def write(self, row: ModelProjectionRow) -> None:
        """Persist a single projection row (idempotent upsert by correlation_id)."""
        self._conn.execute(
            f"""
            INSERT INTO {self._TABLE}
                (correlation_id, workflow, terminal_topic, status, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(correlation_id) DO UPDATE SET
                workflow=excluded.workflow,
                terminal_topic=excluded.terminal_topic,
                status=excluded.status,
                payload=excluded.payload,
                created_at=excluded.created_at
            """,
            (
                str(row.correlation_id),
                row.workflow,
                row.terminal_topic,
                row.status,
                json.dumps(row.payload),
                row.created_at.isoformat(),
            ),
        )
        self._conn.commit()

    def read(self, correlation_id: UUID) -> ModelProjectionRow | None:
        """Read back the projection row for a correlation ID, or None."""
        cursor = self._conn.execute(
            f"""
            SELECT correlation_id, workflow, terminal_topic, status, payload, created_at
            FROM {self._TABLE}
            WHERE correlation_id = ?
            """,
            (str(correlation_id),),
        )
        record = cursor.fetchone()
        if record is None:
            return None
        return ModelProjectionRow(
            correlation_id=UUID(record[0]),
            workflow=record[1],
            terminal_topic=record[2],
            status=record[3],
            payload=json.loads(record[4]),
            created_at=datetime.fromisoformat(record[5]),
        )

    def row_count(self) -> int:
        """Return the number of projection rows (diagnostic helper)."""
        cursor = self._conn.execute(f"SELECT COUNT(*) FROM {self._TABLE}")
        return int(cursor.fetchone()[0])

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()


__all__ = ["SqliteProjectionStore"]
