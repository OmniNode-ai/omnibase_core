# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""GitHub merge queue adapter with strategy-aware dispatch.

Wraps ``gh pr merge`` with automatic detection of merge-queue vs.
squash-auto strategy per repository.

See Also:
    - OMN-7260: Merge strategy detection and conflict handling
    - :class:`MergeStrategyDetector`: Strategy resolution

.. versionadded:: 0.40.0
"""

from __future__ import annotations

import logging
import subprocess

from omnibase_core.adapters.merge_strategy_detector import MergeStrategyDetector
from omnibase_core.enums.enum_merge_strategy import EnumMergeStrategy

logger = logging.getLogger("omnibase")

_ENQUEUE_TIMEOUT = 10


class GitHubMergeQueueAdapter:
    """Enqueue PRs using the correct strategy for the target repository.

    If a :class:`MergeStrategyDetector` is supplied it is used directly;
    otherwise one is created from *owner* and *repo*.
    """

    def __init__(
        self,
        owner: str,
        repo: str,
        strategy_detector: MergeStrategyDetector | None = None,
    ) -> None:
        self.owner = owner
        self.repo = repo
        self._detector = strategy_detector or MergeStrategyDetector(owner, repo)

    def enqueue(self, pr_number: int) -> bool:
        """Enqueue *pr_number* via the repo's merge strategy.

        Returns ``True`` on success, ``False`` on failure.
        """
        strategy = self._detector.detect()

        if strategy == EnumMergeStrategy.MERGE_QUEUE:
            return self._run(
                ["gh", "pr", "merge", str(pr_number), "--auto"],
                pr_number,
                "merge queue",
            )
        return self._run(
            ["gh", "pr", "merge", str(pr_number), "--squash", "--auto"],
            pr_number,
            "squash-auto",
        )

    def _run(self, cmd: list[str], pr_number: int, label: str) -> bool:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_ENQUEUE_TIMEOUT,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("%s enqueue failed for PR #%d: %s", label, pr_number, exc)
            return False

        if result.returncode == 0:
            logger.info("PR #%d enqueued (%s)", pr_number, label)
            return True

        logger.warning(
            "%s enqueue failed for PR #%d: %s",
            label,
            pr_number,
            result.stderr.strip(),
        )
        return False
