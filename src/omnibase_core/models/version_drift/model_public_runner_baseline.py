# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The self-hosted jobs public repositories already carry (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelPublicRunnerBaseline"]


class ModelPublicRunnerBaseline(BaseModel):
    """Per repository, per workflow file, the jobs whose ``runs-on`` was self-hosted.

    Operator ruling 2026-10-16T07:07:09Z: CI runners are for private
    repositories only. The baseline records what public repositories already
    run there and only shrinks: removing a job is allowed, adding one is not.
    A job matches by ``(repo, path, job id)``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repos: dict[str, dict[str, tuple[str, ...]]] = Field(default_factory=dict)

    def entries(self) -> frozenset[tuple[str, str, str]]:
        """Every ``(repo, path, job)`` the baseline records."""
        return frozenset(
            (repo, path, job)
            for repo, files in self.repos.items()
            for path, jobs in files.items()
            for job in jobs
        )
