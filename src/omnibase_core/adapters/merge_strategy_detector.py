# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Merge strategy detection for GitHub repositories.

Detects whether a repository uses a merge queue or requires direct squash
merging via branch protection API.  Results are cached in-memory keyed by
``owner/repo``.

See Also:
    - OMN-7260: Merge strategy detection and conflict handling
    - :class:`GitHubMergeQueueAdapter`: Consumer of merge strategies

.. versionadded:: 0.40.0
"""

from __future__ import annotations

import json
import logging
import subprocess

from omnibase_core.enums.enum_merge_strategy import EnumMergeStrategy

logger = logging.getLogger("omnibase")

_API_TIMEOUT = 10


class MergeStrategyDetector:
    """Detect the merge strategy for a GitHub repository.

    Queries ``gh api repos/{owner}/{repo}/branches/main/protection`` and
    inspects ``required_status_checks.strict`` to determine whether a merge
    queue is active.  Results are cached in-memory keyed by ``owner/repo``.
    """

    _cache: dict[str, EnumMergeStrategy] = {}

    def __init__(self, owner: str, repo: str) -> None:
        self.owner = owner
        self.repo = repo
        self._key = f"{owner}/{repo}"

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()

    def detect(self) -> EnumMergeStrategy:
        """Return the merge strategy for this repository, caching the result."""
        if self._key in self._cache:
            return self._cache[self._key]

        try:
            result = subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{self.owner}/{self.repo}/branches/main/protection",
                ],
                capture_output=True,
                text=True,
                timeout=_API_TIMEOUT,
                check=False,
            )

            if result.returncode != 0:
                logger.debug(
                    "No branch protection for %s, defaulting to SQUASH_AUTO",
                    self._key,
                )
                strategy = EnumMergeStrategy.SQUASH_AUTO
            else:
                strategy = self._parse_strategy(json.loads(result.stdout))
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Merge strategy detection failed for %s (%s), defaulting to SQUASH_AUTO",
                self._key,
                exc,
            )
            strategy = EnumMergeStrategy.SQUASH_AUTO

        self._cache[self._key] = strategy
        return strategy

    def _parse_strategy(self, protection: dict[str, object]) -> EnumMergeStrategy:
        checks = protection.get("required_status_checks")
        if isinstance(checks, dict) and checks.get("strict") is True:
            return EnumMergeStrategy.MERGE_QUEUE
        return EnumMergeStrategy.SQUASH_AUTO

    def get_merge_command(self, pr_number: int) -> list[str]:
        strategy = self.detect()
        base = ["gh", "pr", "merge", str(pr_number)]
        if strategy == EnumMergeStrategy.MERGE_QUEUE:
            return [*base, "--auto"]
        return [*base, "--squash", "--auto"]
