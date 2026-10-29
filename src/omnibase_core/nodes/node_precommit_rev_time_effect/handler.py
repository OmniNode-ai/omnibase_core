# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Git and read-only SQLite effects for pre-commit revision timestamps."""

from __future__ import annotations

import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path

from omnibase_core.models.precommit_pins.model_precommit_rev_time import (
    ModelPrecommitRevTime,
)
from omnibase_core.models.precommit_pins.model_precommit_rev_time_request import (
    ModelPrecommitRevTimeRequest,
)
from omnibase_core.models.precommit_pins.model_precommit_rev_time_result import (
    ModelPrecommitRevTimeResult,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env


class NodePrecommitRevTimeEffect:
    """Own all commit-time lookup I/O; unavailable revisions remain absent."""

    @staticmethod
    def _commit_time(repo: Path, rev: str, timeout: float) -> int | None:
        try:
            result = subprocess.run(
                ["git", "-C", str(repo), "show", "-s", "--format=%ct", rev],
                capture_output=True,
                text=True,
                check=False,
                env=scrub_git_location_env(),
                timeout=timeout,
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except (OSError, ValueError, subprocess.SubprocessError):
            return None
        return None

    def handle(
        self, request: ModelPrecommitRevTimeRequest
    ) -> ModelPrecommitRevTimeResult:
        """Resolve only supplied candidates; never create or modify the cache."""
        params = request.parameters
        times: dict[tuple[str, str], int] = {}
        if not request.pins:
            return ModelPrecommitRevTimeResult(rev_times=())
        if params.history_repo:
            for pin in request.pins:
                timestamp = self._commit_time(
                    Path(params.history_repo).expanduser(),
                    f"{pin.rev}^{{commit}}",
                    params.git_timeout_seconds,
                )
                if timestamp is not None:
                    times[pin.repo, pin.rev] = timestamp
        else:
            home = request.cache_home
            if home is None:
                home = params.cache_home_default
            database = Path(home).expanduser() / params.cache_index_file
            # SQL identifiers are validated by the request model; URL/ref are bound values.
            query = (
                f'SELECT "{params.cache_path_column}" FROM "{params.cache_index_table}" '
                f'WHERE "{params.cache_repo_column}" = ? AND "{params.cache_ref_column}" = ?'
            )
            try:
                with closing(
                    sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
                ) as connection:
                    for pin in request.pins:
                        if (pin.repo, pin.rev) in times:
                            continue
                        for row in connection.execute(query, (pin.repo, pin.rev)):
                            path: object = row[0]
                            if isinstance(path, str):
                                timestamp = self._commit_time(
                                    Path(path), "HEAD", params.git_timeout_seconds
                                )
                                if timestamp is not None:
                                    times[pin.repo, pin.rev] = timestamp
                                    break
            except (OSError, ValueError, sqlite3.Error):
                pass
        return ModelPrecommitRevTimeResult(
            rev_times=tuple(
                ModelPrecommitRevTime(repo=repo, rev=rev, committed_at=stamp)
                for (repo, rev), stamp in sorted(times.items())
            )
        )
