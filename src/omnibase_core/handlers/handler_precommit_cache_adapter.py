# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Commit-time lookups for the pin-parity check (OMN-21433).

The one place the check touches git and the pre-commit cache index. The file name
ends in ``_adapter.py`` because reading the cache index is a raw ``sqlite3`` call,
which the repository allows only at an adapter.
"""

from __future__ import annotations

import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path

from omnibase_core.models.precommit_pins.model_precommit_pin import ModelPrecommitPin
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

__all__ = ["cache_commit_times", "commit_time"]


def commit_time(repo: Path, rev: str) -> int | None:
    """Resolve one commit time; unavailable revisions stay absent from the request."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "show", "-s", "--format=%ct", rev],
            capture_output=True,
            text=True,
            check=False,
            env=scrub_git_location_env(),
            timeout=30,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return None


def cache_commit_times(
    home: Path, pins: tuple[ModelPrecommitPin, ...]
) -> dict[str, int]:
    """Use exact config URL/ref keys and each cached checkout's HEAD, read-only."""
    times: dict[str, int] = {}
    database = home / "db.db"
    try:
        with closing(
            sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
        ) as connection:
            for pin in pins:
                if pin.rev in times:
                    continue
                rows = connection.execute(
                    "SELECT path FROM repos WHERE repo = ? AND ref = ?",
                    (pin.repo, pin.rev),
                )
                for row in rows:
                    path: object = row[0]
                    if isinstance(path, str):
                        committed_at = commit_time(Path(path), "HEAD")
                        if committed_at is not None:
                            times[pin.rev] = committed_at
                            break
    except (OSError, ValueError, sqlite3.Error):
        # Missing or unreadable cache entries leave revs unresolved, hence FAIL.
        return times
    return times
