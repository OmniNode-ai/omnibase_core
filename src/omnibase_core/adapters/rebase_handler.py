# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Rebase conflict handling for PR merge operations.

Provides :func:`attempt_rebase` for automated conflict resolution on
behind/dirty PR branches, with :class:`RebaseResult` as the structured
outcome type.

See Also:
    - OMN-7260: Merge strategy detection and conflict handling

.. versionadded:: 0.40.0
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("omnibase")

_REBASE_TIMEOUT = 60


class RebaseResult:
    """Outcome of a :func:`attempt_rebase` call.

    Exactly one of *success*, *skipped*, or *needs_manual* is ``True``.
    """

    __slots__ = ("message", "needs_manual", "skipped", "success")

    def __init__(
        self,
        *,
        success: bool = False,
        skipped: bool = False,
        needs_manual: bool = False,
        message: str = "",
    ) -> None:
        self.success = success
        self.skipped = skipped
        self.needs_manual = needs_manual
        self.message = message

    @classmethod
    def ok(cls, message: str = "Rebase succeeded") -> RebaseResult:
        return cls(success=True, message=message)

    @classmethod
    def skip(cls, message: str) -> RebaseResult:
        return cls(skipped=True, message=message)

    @classmethod
    def manual(cls, message: str) -> RebaseResult:
        return cls(needs_manual=True, message=message)

    def __repr__(self) -> str:
        tag = "ok" if self.success else ("skip" if self.skipped else "manual")
        return f"RebaseResult({tag}, {self.message!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RebaseResult):
            return NotImplemented
        return (
            self.success == other.success
            and self.skipped == other.skipped
            and self.needs_manual == other.needs_manual
            and self.message == other.message
        )


def attempt_rebase(
    repo_path: Path,
    pr_branch: str,
    main_branch: str = "origin/main",
) -> RebaseResult:
    """Attempt ``git rebase`` on *pr_branch* against *main_branch*.

    Fetches latest refs, then rebases.  On conflict or failure the rebase
    is aborted and :meth:`RebaseResult.manual` is returned.  Failed rebases
    are never retried.
    """
    try:
        fetch = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if fetch.returncode != 0:
            return RebaseResult.manual(f"git fetch failed: {fetch.stderr.strip()}")

        rebase = subprocess.run(
            ["git", "rebase", main_branch],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=_REBASE_TIMEOUT,
            check=False,
        )

        if rebase.returncode == 0:
            logger.info("Rebase succeeded for %s onto %s", pr_branch, main_branch)
            return RebaseResult.ok(f"Rebased {pr_branch} onto {main_branch}")

        _abort_rebase(repo_path)
        stderr_lower = rebase.stderr.lower()
        if "conflict" in stderr_lower:
            logger.warning("Rebase conflict for %s, needs manual resolution", pr_branch)
            return RebaseResult.manual(f"Merge conflicts during rebase of {pr_branch}")
        return RebaseResult.manual(f"Rebase failed: {rebase.stderr.strip()}")

    except subprocess.TimeoutExpired:
        _abort_rebase(repo_path)
        return RebaseResult.manual(f"Rebase timed out for {pr_branch}")


def _abort_rebase(repo_path: Path) -> None:
    subprocess.run(
        ["git", "rebase", "--abort"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
